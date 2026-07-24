# Real Contract Corpus (SEC EDGAR)

Real, negotiated, party-named contracts pulled from SEC EDGAR full-text search
(`efts.sec.gov`) and the EDGAR Archives, for testing the deterministic rules
engine (`rules_engine.py`) against real-world documents rather than
hand-written test sentences. All files are plain text extracted from the
original EDGAR HTML/TXT exhibits (tags stripped, entities decoded); no
substantive text was altered.

Fetched with a proper identifying User-Agent per SEC's fair-access policy
(`TriageCounsel Research contact@triagecounsel.com`).

66 contracts across 12 practice areas, at least 5 per area. Organized into
one subfolder per practice area.

## 01_real_estate — Real estate purchase & sale agreements (5)

| File | Parties | Source |
|---|---|---|
| `01_real_estate_purchase_sale_agreement_hartman_xx_2014.txt` | U.S. Bank Nat'l Assoc. (Trustee) / Hartman XX Limited Partnership | [8-K EX-10.1, 2014-11-18](https://www.sec.gov/Archives/edgar/data/1446687/000144668714000072/psacopperfieldtimbercreek.htm) |
| `farmer_brothers_purchase_sale_2016.txt` | Farmer Bros. Co. (Seller) | [8-K EX-10.41, 2016-05-06](https://www.sec.gov/Archives/edgar/data/34563/000003456316000104/farm-ex1041purchaseandsale.htm) |
| `cim_reft_coyote_portfolio_psa_2019.txt` | CIM Real Estate Finance Trust (Coyote Portfolio) | [8-K EX-10.1, 2019-09-03](https://www.sec.gov/Archives/edgar/data/1498547/000149854719000046/ex101purchaseagreement-pro.htm) |
| `preferred_apartment_communities_psa_2014.txt` | Preferred Apartment Communities (Dunbar) | [8-K EX-10.1, 2014-07-28](https://www.sec.gov/Archives/edgar/data/1481832/000148183214000071/agreementofpurchaseandsale.htm) |
| `cole_office_industrial_reit_psa_2019.txt` | Cole Office & Industrial REIT (National Credit Industrial Portfolio) | [8-K EX-10.1, 2019-02-15](https://www.sec.gov/Archives/edgar/data/1572758/000157275819000008/purchaseagreementfornation.htm) |

## 02_insurance — Insurance program / MGA / reinsurance agreements (5)

| File | Parties | Source |
|---|---|---|
| `02_insurance_loss_portfolio_transfer_reinsurance_james_river_2021.txt` | James River Insurance Co. / James River Casualty Co. / Aleka Insurance, Inc. | [8-K EX-10.1, 2021-09-30](https://www.sec.gov/Archives/edgar/data/1620459/000110465921120933/tm2128750d1_ex10-1.htm) |
| `american_coastal_program_administrator_2024.txt` | American Coastal Insurance Corp — Program Administrator Agreement | [10-K EX-1.2, 2024-05-14](https://www.sec.gov/Archives/edgar/data/1401521/000140152124000045/programadministratoragre.htm) |
| `american_physicians_insurance_mga_2007.txt` | American Physicians Insurance Company — Managing General Agency Agreement | [10-K EX-10.1, 2007-04-30](https://www.sec.gov/Archives/edgar/data/1378026/000115895707000097/exhibit101.htm) |
| `north_pointe_insurance_mga_2006.txt` | North Pointe Insurance Company — Managing General Agency Agreement | [10-K EX-10.37, 2007-03-30](https://www.sec.gov/Archives/edgar/data/1171218/000095012407001900/k13130exv10w37.htm) |
| `republic_companies_mga_2006.txt` | Republic Companies Group — Amended and Restated MGA Agreement | [10-K EX-10.14, 2006-03-30](https://www.sec.gov/Archives/edgar/data/1320092/000119312506068740/dex1014.htm) |

## 03_credit_agreement — Credit agreements / promissory notes / guaranties (7)

| File | Parties | Source |
|---|---|---|
| `03a_credit_agreement_callon_petroleum_regions_bank_2010.txt` | Callon Petroleum Company / Regions Bank et al. (Third A&R Credit Agreement) | [8-K EX-10.1, 2010-02-03](https://www.sec.gov/Archives/edgar/data/928022/000095012310008205/h69502exv10w1.htm) |
| `03b_promissory_note_callon_petroleum_2010.txt` | Callon Petroleum Company / Regions Bank (companion note) | [8-K EX-10.2, 2010-02-03](https://www.sec.gov/Archives/edgar/data/928022/000095012310008205/h69502exv10w2.htm) |
| `03c_guaranty_agreement_callon_petroleum_2010.txt` | Callon subsidiaries (Guarantors) / Regions Bank (companion guaranty) | [8-K EX-10.3, 2010-02-03](https://www.sec.gov/Archives/edgar/data/928022/000095012310008205/h69502exv10w3.htm) |
| `sybron_dental_specialties_credit_agreement_2006.txt` | Sybron Dental Specialties, Inc. / Kerr Corporation et al. | [8-K EX-10.1, 2006-03-29](https://www.sec.gov/Archives/edgar/data/1121302/000119312506066480/dex101.htm) |
| `john_wiley_sons_bofa_credit_amendment_2022.txt` | John Wiley & Sons, Inc. / Bank of America | [8-K EX-10.1, 2022-12-06](https://www.sec.gov/Archives/edgar/data/107140/000010714022000088/exhibit101bofa_johnwileyxs.htm) |
| `handleman_credit_guaranty_amendment_2008.txt` | Handleman Company — Tenth Amendment to Credit and Guaranty Agreement | [8-K EX-10.1, 2008-08-06](https://www.sec.gov/Archives/edgar/data/314727/000095015208006089/k34542exv10w1.htm) |
| `marten_transport_credit_amendment_2011.txt` | Marten Transport, Ltd. — Third Amendment to Credit Agreement | [8-K EX-10.1, 2011-05-31](https://www.sec.gov/Archives/edgar/data/799167/000143774911003718/ex10-1.htm) |

## 04_government_subcontract — Government prime/subcontracts (FAR/DFARS) (5)

| File | Parties | Source |
|---|---|---|
| `04_government_subcontract_bae_antenna_products_2005.txt` | BAE Systems Advanced Technologies / Antenna Products Corp. (Navy prime N00014-02-D-0479) | [8-K EX-10.B, 2005-02-07](https://www.sec.gov/Archives/edgar/data/724267/000101738605000014/bae_sub-contract.txt) |
| `force_protection_general_dynamics_mrap_subcontract_2008.txt` | General Dynamics Land Systems / Force Protection Inc. (MRAP subcontract) | [10-K EX-10.52, 2008-09-15](https://www.sec.gov/Archives/edgar/data/1032863/000104746908010069/a2187693zex-10_52.htm) |
| `itt_corp_us_army_compliance_agreement_2007.txt` | United States Army / ITT Corp — Administrative Compliance Agreement | [8-K EX-99.1, 2007-10-12](https://www.sec.gov/Archives/edgar/data/216228/000089808007000303/agreement.txt) |
| `flight_international_group_award_contract_2002.txt` | Flight International Group — U.S. Government Award/Contract | [8-K EX-10(v), 2002-08-19](https://www.sec.gov/Archives/edgar/data/732775/000113207202000272/s11-3049_ex10v.txt) |
| `cree_navy_prime_contract_2002.txt` | Cree, Inc. — U.S. Navy prime contract N00014-02-C-0306 | [10-K EX-10.28, 2003-09-25](https://www.sec.gov/Archives/edgar/data/895419/000119312503054147/dex1028.htm) |

## 05_healthcare — Healthcare services / physician agreements (5)

| File | Parties | Source |
|---|---|---|
| `05_physician_employment_agreement_21st_century_oncology_2012.txt` | 21st Century Oncology, LLC / Daniel E. Dosoretz, M.D. | [8-K EX-10.4, 2012-06-15](https://www.sec.gov/Archives/edgar/data/1503518/000110465912043747/a12-14715_1ex10d4.htm) |
| `genoptix_medical_director_agreement_2009.txt` | Genoptix, Inc. — Amended and Restated Medical Director Agreement | [10-K EX-10.28, 2009-02-26](https://www.sec.gov/Archives/edgar/data/1138412/000119312509039085/dex1028.htm) |
| `fuse_medical_medical_director_agreement_2014.txt` | Fuse Medical, Inc. — Medical Director Agreement | [8-K EX-10.4, 2014-08-29](https://www.sec.gov/Archives/edgar/data/319016/000147793214004849/teee_ex104.htm) |
| `aac_holdings_medical_staffing_services_2015.txt` | AAC Holdings, Inc. — Professional Services Agreement for Medical Staffing | [10-K EX-10.18, 2016-03-09](https://www.sec.gov/Archives/edgar/data/1606180/000156459016014247/aac-ex1018_642.htm) |
| `wellcare_florida_ahca_standard_contract_2006.txt` | WellCare Health Plans / State of Florida Agency for Health Care Administration | [8-K EX-10.1, 2006-09-01](https://www.sec.gov/Archives/edgar/data/1279363/000127936306000078/exhibit_10-1.htm) |

## 06_ip_trademark_license — IP / trademark license agreements (5)

| File | Parties | Source |
|---|---|---|
| `06_trademark_license_agreement_eli_lilly_elanco_2018.txt` | Eli Lilly and Company (Licensor) / Elanco Animal Health (Licensee) | [8-K EX-10.7, 2018-09-26](https://www.sec.gov/Archives/edgar/data/1739104/000104746918006441/a2236778zex-10_7.htm) |
| `estee_lauder_aerin_license_agreement_2011.txt` | Aerin LLC / Aerin Lauder Zinterhofer / Estée Lauder Inc. | [8-K EX-10.2, 2011-04-08](https://www.sec.gov/Archives/edgar/data/1001250/000090951811000147/mm04-0511_8ke102.htm) |
| `schiff_nutrition_ganeden_ip_license_2011.txt` | Ganeden Biotech, Inc. — Intellectual Property License Agreement | [8-K EX-10.1, 2011-06-03](https://www.sec.gov/Archives/edgar/data/1022368/000102236811000029/exhibit10_1-ipagreement.htm) |
| `american_outdoor_brands_trademark_license_2024.txt` | American Outdoor Brands, Inc. — Amended and Restated Trademark License Agreement | [8-K EX-10.1, 2024-04-16](https://www.sec.gov/Archives/edgar/data/1808997/000095017024044829/aout-ex10_1.htm) |
| `carrier_global_license_agreement_2023.txt` | Carrier Global Corp — Form of License Agreement (SPA exhibit; redacted) | [8-K EX-10.1, 2023-04-26](https://www.sec.gov/Archives/edgar/data/1783180/000095014223001205/eh230352031_ex1001.htm) |

## 07_franchise — Franchise agreements (6)

| File | Parties | Source |
|---|---|---|
| `07_master_franchise_agreement_wayback_burgers_japan_2021.txt` | WB Burgers Asia, Inc. (Wayback Burgers) — Master Franchise Agreement (Japan; redacted signature copy, executed original retained) | [8-K EX-10.2, 2021-09-16](https://www.sec.gov/Archives/edgar/data/1787412/000159991621000211/masterfranchisecopy.htm) |
| `ryans_family_steakhouses_franchise_agreement_1987.txt` | Ryan's Family Steak Houses, Inc. — Franchise Agreement | [10-K EX-10.21, 2002-03-28](https://www.sec.gov/Archives/edgar/data/355622/000035562202000021/franchiseagmt1987.txt) |
| `diversified_restaurant_bagger_daves_area_development_2011.txt` | Bagger Dave's Franchising Corp — Area Development Agreement | [8-K EX-10.1, 2011-11-23](https://www.sec.gov/Archives/edgar/data/1394156/000139843211000948/ex10-1.htm) |
| `applebees_standard_form_franchise_agreement_2004.txt` | Applebee's Neighborhood Grill & Bar — Standard Form Franchise Agreement | [10-K EX-10, 2004-03-12](https://www.sec.gov/Archives/edgar/data/853665/000085366504000067/franchiseagmt.txt) |
| `krispy_kreme_form_franchise_agreement_2008.txt` | Krispy Kreme Doughnut Corporation — Form of Franchise Agreement | [8-K EX-10.3, 2008-04-17](https://www.sec.gov/Archives/edgar/data/1100270/000120677408000807/exhibit10-3.htm) |
| `family_steak_houses_florida_franchise_amendment_2002.txt` | Family Steak Houses of Florida — Amendment to Franchise Agreement | [10-K EX-10, 2002-03-29](https://www.sec.gov/Archives/edgar/data/784539/000091960702000101/ex10-19.txt) |

## 08_settlement — Settlement agreements (4)

| File | Parties | Source |
|---|---|---|
| `08_settlement_agreement_release_retractable_technologies_bd_2019.txt` | Retractable Technologies, Inc. / Thomas J. Shaw v. Becton, Dickinson and Company / MDC Investment Holdings (patent litigation) | [8-K EX-99.2, 2019-05-08](https://www.sec.gov/Archives/edgar/data/946563/000110465919027721/a19-9540_1ex99d2.htm) |
| `harleysville_national_ceo_settlement_release_2006.txt` | Harleysville National Corporation — CEO Settlement Agreement and General Release | [8-K EX-99.1, 2006-12-13](https://www.sec.gov/Archives/edgar/data/702902/000070290206000073/settlementagmt-release.htm) |
| `lucas_energy_victory_energy_settlement_mutual_release_2015.txt` | Lucas Energy, Inc. / Victory Energy Corporation — Settlement Agreement and Mutual Release | [8-K EX-10.1, 2015-06-30](https://www.sec.gov/Archives/edgar/data/1309082/000121478215000045/ex10-1.htm) |
| `exegenics_pfost_settlement_agreement_2007.txt` | eXegenics Inc — Pfost Settlement Agreement and General Release | [8-K EX-10.1, 2007-05-11](https://www.sec.gov/Archives/edgar/data/944809/000095014407004724/g07413exv10w1.htm) |
| `yelp_class_action_stipulation_settlement_2022.txt` | Yelp Inc. — Stipulation of Settlement (securities class action) | [8-K EX-99.1, 2022-06-30](https://www.sec.gov/Archives/edgar/data/1345016/000134501622000050/stipulationofsettlement.htm) |

## 09_executive_employment — Executive employment / severance agreements (5)

| File | Parties | Source |
|---|---|---|
| `09_executive_transition_severance_agreement_carecom_marcelo_2019.txt` | Care.com, Inc. / Sheila Lirio Marcelo (Founder, CEO & President) | [8-K EX-10.1, 2019-08-06](https://www.sec.gov/Archives/edgar/data/1412270/000141227019000037/exhibit101sheilamarcelotra.htm) |
| `transdigm_amended_restated_employment_agreement_2016.txt` | TransDigm Group Incorporated — Amended and Restated Employment Agreement | [8-K EX-10.1, 2016-12-15](https://www.sec.gov/Archives/edgar/data/1260221/000126022116000115/ex101employmentagreement-s.htm) |
| `answerthink_employment_agreement_amendment_2005.txt` | Answerthink, Inc. — Second Amendment to Employment Agreement | [8-K EX-10.1, 2005-08-09](https://www.sec.gov/Archives/edgar/data/1057379/000119312505160994/dex101.htm) |
| `education_management_executive_letter_agreement_2006.txt` | Education Management Corporation / J. William Brooks — Executive Letter Agreement | [8-K EX-10.2, 2006-03-09](https://www.sec.gov/Archives/edgar/data/880059/000095015206001908/j1902601exv10w2.txt) |
| `coach_inc_employment_agreement_amendment_2013.txt` | Coach, Inc. — Amendment to Employment Agreement | [8-K EX-10.1, 2013-12-23](https://www.sec.gov/Archives/edgar/data/1116132/000115752313005879/a50771708ex10_1.htm) |

## 10_ma_purchase_agreement — M&A stock/asset purchase agreements (escrow, MAC, working capital adjustment) (5)

| File | Parties | Source |
|---|---|---|
| `10_stock_purchase_agreement_leeds_equity_datamark_ecollege_2003.txt` | Leeds Equity Partners III, L.P. et al. / Datamark Inc. / eCollege.com | [8-K EX-2.1, 2003-11-03](https://www.sec.gov/Archives/edgar/data/1085653/000108565303000078/ex2_1spa.htm) |
| `brightcove_unicorn_media_asset_purchase_agreement_2014.txt` | Brightcove Inc. / Cacti Acquisition LLC / Unicorn Media, Inc. et al. | [8-K EX-2.1, 2014-01-06](https://www.sec.gov/Archives/edgar/data/1313275/000114420414000599/v364700_ex2-1.htm) |
| `northwest_pipe_asset_purchase_agreement_2017.txt` | Northwest Pipe Company / Almacenadora Afirme, S.A. de C.V. | [8-K EX-2.1, 2017-12-29](https://www.sec.gov/Archives/edgar/data/1001385/000143774917021315/ex_102508.htm) |
| `dj_orthopedics_stock_purchase_agreement_2006.txt` | DJ Orthopedics, LLC / Tailwind Stockholders / DLJ Stockholders et al. | [8-K EX-10.2, 2006-04-13](https://www.sec.gov/Archives/edgar/data/1157972/000110465906025032/a06-8547_1ex10d2.htm) |
| `rainmaker_n3_asset_purchase_agreement_2014.txt` | N3 North America, LLC (Purchaser) / Rainmaker Systems, Inc. | [8-K EX-10.1, 2014-10-17](https://www.sec.gov/Archives/edgar/data/1094007/000109400714000041/a101-rainmakerxn3apa.htm) |

## 11_llc_partnership — Partnership / LLC operating agreements (5)

| File | Parties | Source |
|---|---|---|
| `11_llc_operating_agreement_redwood_intermediate_2021.txt` | Redwood Intermediate, LLC — Fourth Amended and Restated LLC Agreement | [8-K EX-10.3, 2021-10-28](https://www.sec.gov/Archives/edgar/data/1820201/000110465921131160/tm2130841d1_ex10-3.htm) |
| `parsley_energy_llc_agreement_2014.txt` | Parsley Energy, LLC — First Amended and Restated LLC Agreement | [8-K EX-10.1, 2014-06-04](https://www.sec.gov/Archives/edgar/data/1594466/000119312514225854/d736716dex101.htm) |
| `fc_gen_operations_genesis_healthcare_llc_agreement_2015.txt` | FC-GEN Operations Investment, LLC (Genesis Healthcare) — Sixth A&R LLC Operating Agreement | [8-K EX-10.1, 2015-02-06](https://www.sec.gov/Archives/edgar/data/1351051/000119312515037418/d858815dex101.htm) |
| `malibu_boats_holdings_llc_agreement_2014.txt` | Malibu Boats Holdings, LLC — First Amended and Restated LLC Agreement | [8-K EX-10.1, 2014-02-06](https://www.sec.gov/Archives/edgar/data/1590976/000119312514038886/d672080dex101.htm) |
| `macwh_lp_macerich_limited_partnership_agreement_2005.txt` | MACWH, LP (The Macerich Company) — 2005 A&R Agreement of Limited Partnership | [8-K EX-10.1, 2005-04-29](https://www.sec.gov/Archives/edgar/data/912242/000110465905019358/a05-7552_1ex10d1.htm) |

## 12_construction — Construction contracts (AIA-style / GMP) (5)

| File | Parties | Source |
|---|---|---|
| `12_construction_contract_aia_a111_pnk_manhattan_construction_2003.txt` | PNK (Lake Charles), L.L.C. (Owner) / Manhattan Construction Company (Contractor) — AIA A111-1997 | [8-K EX-10.2, 2003-09-19](https://www.sec.gov/Archives/edgar/data/356213/000119312503051822/dex102.htm) |
| `century_casinos_sprung_aia_a111_gmp_construction_2005.txt` | Century Casinos / Sprung Construction — AIA A111-1997 GMP Construction Contract | [8-K EX-10.161, 2005-12-13](https://www.sec.gov/Archives/edgar/data/911147/000091114705000097/ex10_161.htm) |
| `wynn_las_vegas_gmp_construction_change_order_2006.txt` | Wynn Las Vegas — Agreement/Change Order for Guaranteed Maximum Price Construction Services | [10-K EX-10.12, 2006-03-16](https://www.sec.gov/Archives/edgar/data/1174922/000119312506055625/dex1012.htm) |
| `addvantage_technologies_construction_services_agreement_2007.txt` | ADDvantage Technologies Group — Construction Services with General Conditions Agreement | [8-K EX-10.1, 2007-05-16](https://www.sec.gov/Archives/edgar/data/874292/000135585607000020/construction_contract.htm) |
| `roberts_realty_aia_a117_construction_agreement_2006.txt` | Roberts Realty Investors — AIA Document A117-1987 Abbreviated Form Owner/Contractor Agreement | [8-K EX-10.2, 2006-02-22](https://www.sec.gov/Archives/edgar/data/1011109/000094270806000028/ex10-2_022206.htm) |

## Notes

- All documents are real, executed (or explicitly stated to have a duly
  executed counterpart on file) agreements between named parties, with
  documented exceptions:
  - The Wayback Burgers master franchise agreement is filed as an unsigned
    copy with signatures/personal information redacted; the filer's cover
    statement confirms the company retains a duly executed, signed original.
  - The Applebee's and Krispy Kreme franchise agreements are filed as
    "Standard Form" / "Form of" documents (no counter-signed version was
    found in EDGAR full-text search for these two filers) — used per the
    task's fallback allowance since they are otherwise well-drafted,
    heavily negotiated industry-standard forms.
  - The Carrier Global trademark license is a "Form of License Agreement"
    exhibit attached to a stock purchase agreement, with a redacted pricing
    section.
  - Several credit-agreement, employment, and franchise entries are
    amendments to (rather than the original execution of) an underlying
    agreement; amendments are themselves real negotiated contracts and a
    plausible real-world upload target for the tool.
- Files `03a`-`03c` are three related exhibits from one Callon Petroleum
  filing (credit agreement, promissory note, guaranty) rather than three
  independent contracts, since a credit agreement filing naturally bundles
  a note and guaranty together.
