"""
Background worker for contract analysis jobs.

Uses a simple Redis-based job queue. Can be run as:
    python worker.py

For production with arq:
    arq worker.WorkerSettings
"""
from __future__ import annotations

import os
import platform
import time
import logging
from datetime import datetime
from typing import Dict, Optional

from dotenv import load_dotenv
load_dotenv()

from database import SessionLocal
from models import AnalysisJob, Contract, ApiUsage, Playbook
from rules_engine import RuleEngine
from evaluator import LLMEvaluator
from playbook_engine import PlaybookEngine
import redis_client
from triage_logging import setup_logging, get_logger, LogContext, generate_analysis_id
from triage_logging.infrastructure import (
    log_worker_processing, log_redis_event, log_job_completion,
    log_performance_summary,
)
from triage_logging.llm import log_llm_call

setup_logging()
logger = get_logger(__name__)

rule_engine = RuleEngine()
llm_evaluator = LLMEvaluator()
playbook_engine = PlaybookEngine()

WORKER_ID = f"worker-{platform.node()}-{os.getpid()}"
MAX_RETRIES = 3
JOB_TIMEOUT = 120


def process_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        with LogContext(analysis_id=job.analysis_id, job_id=job_id, user_id=job.user_id):
            log_worker_processing(WORKER_ID, job_id)
            job.status = "processing"
            job.started_at = datetime.utcnow()
            job.worker_id = WORKER_ID
            job.progress = 10
            db.commit()

            # Get contract text from Redis or DB
            contract_text = redis_client.get_job_payload(str(job_id))
            if not contract_text:
                job.status = "failed"
                job.error_message = "Contract text not found"
                job.completed_at = datetime.utcnow()
                db.commit()
                return

            start_time = time.perf_counter()
            stages: Dict[str, int] = {}

            # Rule engine analysis
            t0 = time.perf_counter()
            analysis = rule_engine.analyze(contract_text)
            stages["Rule Engine"] = int((time.perf_counter() - t0) * 1000)
            job.progress = 40
            db.commit()

            findings = analysis["findings"]
            overall_risk = analysis["overall_risk"]
            findings_dict = [
                {
                    "rule_id": f.rule_id, "rule_name": f.rule_name, "title": f.title,
                    "severity": f.severity.value, "rationale": f.rationale,
                    "matched_excerpt": f.matched_excerpt, "position": f.position,
                    "context": f.context, "clause_number": f.clause_number,
                    "matched_keywords": f.matched_keywords, "aliases": f.aliases,
                }
                for f in findings
            ]

            # LLM evaluation
            t0 = time.perf_counter()
            try:
                llm_result = llm_evaluator.evaluate(
                    findings=findings_dict, overall_risk=overall_risk, contract_text=None
                )
                if not llm_result:
                    llm_result = llm_evaluator.create_fallback_response(
                        findings=findings_dict, overall_risk=overall_risk
                    )
            except Exception:
                llm_result = llm_evaluator.create_fallback_response(
                    findings=findings_dict, overall_risk=overall_risk
                )
            llm_ms = int((time.perf_counter() - t0) * 1000)
            stages["OpenAI"] = llm_ms
            job.progress = 70
            db.commit()

            # Playbook comparison
            deviations = None
            if job.playbook_id:
                t0 = time.perf_counter()
                playbook = db.query(Playbook).filter(Playbook.id == job.playbook_id).first()
                if playbook and playbook.template_findings_json:
                    deviations = playbook_engine.compare(findings_dict, playbook.template_findings_json)
                stages["Playbook"] = int((time.perf_counter() - t0) * 1000)

            job.progress = 85
            db.commit()

            # Save contract
            t0 = time.perf_counter()
            total_ms = int((time.perf_counter() - start_time) * 1000)
            contract = Contract(
                user_id=job.user_id,
                filename=job.filename or "unknown",
                contract_text=contract_text,
                overall_risk=overall_risk,
                findings_json=findings_dict,
                llm_result_json=llm_result,
                rule_counts_json=analysis.get("rule_counts", {"high": 0, "medium": 0, "low": 0}),
                rule_engine_version=analysis.get("version", "1.0.3"),
                analysis_completed=True,
                playbook_id=job.playbook_id,
                deviations_json=deviations,
                analysis_duration_ms=total_ms,
                file_size_bytes=job.file_size_bytes,
            )
            db.add(contract)
            db.flush()
            stages["Database Save"] = int((time.perf_counter() - t0) * 1000)

            # Update job
            job.status = "completed"
            job.contract_id = contract.id
            job.completed_at = datetime.utcnow()
            job.progress = 100

            # Record API usage
            usage = ApiUsage(
                user_id=job.user_id,
                contract_id=contract.id,
                job_id=job.id,
                model=llm_evaluator.model,
                latency_ms=llm_ms,
            )
            db.add(usage)
            db.commit()

            log_performance_summary(stages)
            log_job_completion(
                analysis_id=job.analysis_id,
                execution_time_s=(time.perf_counter() - start_time),
                rules_loaded=len(rule_engine.rules),
                rules_executed=len(rule_engine.rules),
                rules_triggered=len(findings),
                rules_suppressed=len(analysis.get("suppression_log", {})),
                errors=0,
                warnings=0,
            )

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        try:
            job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
            if job:
                job.retry_count = (job.retry_count or 0) + 1
                if job.retry_count >= MAX_RETRIES:
                    job.status = "failed"
                    job.error_message = str(e)[:1000]
                    job.completed_at = datetime.utcnow()
                else:
                    job.status = "pending"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def run_worker():
    logger.info(f"Worker {WORKER_ID} starting, polling for jobs...")
    while True:
        job_data = redis_client.dequeue_job("analysis")
        if job_data:
            job_id = job_data.get("job_id")
            if job_id:
                try:
                    process_job(int(job_id))
                except Exception as e:
                    logger.error(f"Failed to process job {job_id}: {e}")
        else:
            time.sleep(1)


# arq worker settings
try:
    import arq

    async def arq_analyze_contract(ctx, job_id: int):
        process_job(job_id)

    class WorkerSettings:
        functions = [arq_analyze_contract]
        redis_settings = arq.connections.RedisSettings.from_dsn(
            os.getenv("REDIS_URL", "redis://localhost:6379")
        ) if os.getenv("REDIS_URL") else arq.connections.RedisSettings()
        max_jobs = 20
        job_timeout = JOB_TIMEOUT
        max_tries = MAX_RETRIES
except ImportError:
    pass


if __name__ == "__main__":
    run_worker()
