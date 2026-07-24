-- Builds a validation-first, demo-scope agricultural yield database.
-- Source data is attached read-only and never changed by this script.

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = DELETE;

ATTACH DATABASE 'crops.db' AS raw;

CREATE TABLE build_metadata (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

INSERT INTO build_metadata VALUES
  ('schema_version', '1'),
  ('built_utc', strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  ('purpose', 'Validated district-level yields for the AgriSense demo crop set'),
  ('validation_policy', 'Only enabled crops with explicit bounds are eligible for recommendation or finance.'),
  ('source_file', 'crops.db'),
  ('source_file_provenance', 'Not embedded in supplied database; verify and replace with exact BBS yearbook citation before public submission.'),
  ('license_status', 'Unknown: source verification required before redistribution');

CREATE TABLE source_registry (
  source_id TEXT PRIMARY KEY,
  source_name TEXT NOT NULL,
  source_url TEXT,
  publication_or_table TEXT,
  units_original TEXT,
  provenance_status TEXT NOT NULL CHECK (provenance_status IN ('pending_verification','verified')),
  notes TEXT NOT NULL
);

INSERT INTO source_registry VALUES
  ('crops_db_import', 'Supplied crops.db import', NULL, NULL, 'hectares; metric tonnes', 'pending_verification',
   'The supplied SQLite file lacks source URLs, pages, extraction method, and source-year mappings. Do not describe this as BBS-verified until this record is completed.');

CREATE TABLE district_master (
  canonical_district TEXT PRIMARY KEY
);

INSERT INTO district_master VALUES
  ('Bagerhat'),('Bandarban'),('Barguna'),('Barishal'),('Bhola'),('Bogura'),('Brahmanbaria'),('Chapainawabganj'),
  ('Chandpur'),('Chattogram'),('Chuadanga'),('Cox''s Bazar'),('Cumilla'),('Dhaka'),('Dinajpur'),('Faridpur'),
  ('Feni'),('Gaibandha'),('Gazipur'),('Gopalganj'),('Habiganj'),('Jamalpur'),('Jashore'),('Jhalokathi'),
  ('Jhenaidah'),('Joypurhat'),('Khagrachhari'),('Khulna'),('Kishoreganj'),('Kurigram'),('Kushtia'),('Lakshmipur'),
  ('Lalmonirhat'),('Madaripur'),('Magura'),('Manikganj'),('Maulvibazar'),('Meherpur'),('Munshiganj'),('Mymensingh'),
  ('Naogaon'),('Narail'),('Narayanganj'),('Narsingdi'),('Natore'),('Netrokona'),('Nilphamari'),('Noakhali'),
  ('Pabna'),('Panchagarh'),('Patuakhali'),('Pirojpur'),('Rajbari'),('Rajshahi'),('Rangamati'),('Rangpur'),
  ('Satkhira'),('Shariatpur'),('Sherpur'),('Sirajganj'),('Sunamganj'),('Sylhet'),('Tangail'),('Thakurgaon');

CREATE TABLE district_alias (
  raw_district TEXT PRIMARY KEY,
  canonical_district TEXT NOT NULL REFERENCES district_master(canonical_district),
  normalization_reason TEXT NOT NULL
);

-- Explicit aliases only. All other names must exactly match district_master after trimming.
INSERT INTO district_alias VALUES
  ('Chapai Nawabganj', 'Chapainawabganj', 'standardized spelling'),
  ('Cox’s Bazar', 'Cox''s Bazar', 'normalized apostrophe'),
  ('Jessore', 'Jashore', 'current official spelling'),
  ('Munsigonj', 'Munshiganj', 'corrected spelling'),
  ('Mymensinghh', 'Mymensingh', 'corrected spelling');

CREATE TABLE crop_catalog (
  crop_key TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  enabled_for_recommendation INTEGER NOT NULL CHECK (enabled_for_recommendation IN (0,1)),
  source_available INTEGER NOT NULL CHECK (source_available IN (0,1)),
  notes TEXT NOT NULL
);

INSERT INTO crop_catalog VALUES
  ('aman_hyv', 'Aman HYV rice', 1, 1, 'District yield source available and bounded.'),
  ('boro_hyv', 'Boro HYV rice', 1, 1, 'District yield source available and bounded.'),
  ('potato_hyv', 'HYV potato', 1, 1, 'District yield source available and bounded.'),
  ('lentil_masur', 'Lentil (masur)', 1, 1, 'District yield source available and bounded.'),
  ('mustard', 'Mustard', 1, 1, 'District yield source available and bounded.'),
  ('wheat', 'Wheat', 0, 0, 'No literal wheat crop key exists in supplied crop_data; do not calculate its district yield or profit from this import.');

CREATE TABLE crop_yield_bounds (
  crop_key TEXT PRIMARY KEY REFERENCES crop_catalog(crop_key),
  min_kg_per_ha REAL NOT NULL CHECK (min_kg_per_ha > 0),
  max_kg_per_ha REAL NOT NULL CHECK (max_kg_per_ha > min_kg_per_ha),
  rationale TEXT NOT NULL
);

INSERT INTO crop_yield_bounds VALUES
  ('aman_hyv', 1500, 5000, 'Conservative validation band for district aggregate yield.'),
  ('boro_hyv', 2000, 7000, 'Conservative validation band for district aggregate yield.'),
  ('potato_hyv', 5000, 50000, 'Broad validation band; rejects clear unit/parse errors while retaining plausible production.'),
  ('lentil_masur', 500, 5000, 'Conservative validation band for district aggregate yield.'),
  ('mustard', 500, 8000, 'Conservative validation band for district aggregate yield.');

CREATE TABLE rejected_crop_rows (
  source_row_id INTEGER PRIMARY KEY,
  crop_key_raw TEXT NOT NULL,
  district_raw TEXT NOT NULL,
  year TEXT NOT NULL,
  hectares REAL,
  production_mt REAL,
  computed_kg_per_ha REAL,
  rejection_reason TEXT NOT NULL,
  source_id TEXT NOT NULL REFERENCES source_registry(source_id)
);

CREATE TABLE crop_yield_observations (
  observation_id INTEGER PRIMARY KEY,
  source_row_id INTEGER NOT NULL UNIQUE,
  crop_key TEXT NOT NULL REFERENCES crop_catalog(crop_key),
  district TEXT NOT NULL REFERENCES district_master(canonical_district),
  year TEXT NOT NULL CHECK (year GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]'),
  hectares REAL NOT NULL CHECK (hectares > 0),
  production_mt REAL NOT NULL CHECK (production_mt > 0),
  yield_kg_per_ha REAL NOT NULL CHECK (yield_kg_per_ha > 0),
  source_id TEXT NOT NULL REFERENCES source_registry(source_id),
  CHECK (length(year) = 7)
);

WITH classified AS (
  SELECT r.id, r.crop_name, r.district, r.year, r.hectares, r.production_mt,
    CASE WHEN a.canonical_district IS NOT NULL THEN a.canonical_district ELSE trim(r.district) END AS normalized_district,
    CASE
      WHEN c.crop_key IS NULL THEN 'UNSUPPORTED_CROP'
      WHEN d.canonical_district IS NULL THEN 'INVALID_DISTRICT'
      WHEN r.hectares IS NULL OR r.hectares <= 0 THEN 'INVALID_AREA'
      WHEN r.production_mt IS NULL OR r.production_mt <= 0 THEN 'INVALID_PRODUCTION'
      WHEN r.year NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' OR length(r.year) <> 7 THEN 'INVALID_YEAR'
      WHEN (1000.0 * r.production_mt / r.hectares) < b.min_kg_per_ha OR (1000.0 * r.production_mt / r.hectares) > b.max_kg_per_ha THEN 'YIELD_OUTSIDE_VALIDATION_BOUNDS'
      ELSE NULL
    END AS rejection_reason,
    CASE WHEN r.hectares > 0 AND r.production_mt > 0 THEN 1000.0 * r.production_mt / r.hectares END AS yield_kg_per_ha
  FROM raw.crop_data r
  LEFT JOIN district_alias a ON a.raw_district = trim(r.district)
  LEFT JOIN district_master d ON d.canonical_district = COALESCE(a.canonical_district, trim(r.district))
  LEFT JOIN crop_catalog c ON c.crop_key = r.crop_name AND c.enabled_for_recommendation = 1
  LEFT JOIN crop_yield_bounds b ON b.crop_key = r.crop_name
)
INSERT INTO rejected_crop_rows
SELECT id, crop_name, district, year, hectares, production_mt, yield_kg_per_ha, rejection_reason, 'crops_db_import'
FROM classified WHERE rejection_reason IS NOT NULL;

WITH classified AS (
  SELECT r.id, r.crop_name, r.district, r.year, r.hectares, r.production_mt,
    COALESCE(a.canonical_district, trim(r.district)) AS normalized_district,
    CASE
      WHEN c.crop_key IS NULL OR d.canonical_district IS NULL OR r.hectares IS NULL OR r.hectares <= 0
        OR r.production_mt IS NULL OR r.production_mt <= 0 OR r.year NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]'
        OR length(r.year) <> 7 THEN 0
      WHEN (1000.0 * r.production_mt / r.hectares) < b.min_kg_per_ha OR (1000.0 * r.production_mt / r.hectares) > b.max_kg_per_ha THEN 0
      ELSE 1
    END AS accepted,
    1000.0 * r.production_mt / r.hectares AS yield_kg_per_ha
  FROM raw.crop_data r
  LEFT JOIN district_alias a ON a.raw_district = trim(r.district)
  LEFT JOIN district_master d ON d.canonical_district = COALESCE(a.canonical_district, trim(r.district))
  LEFT JOIN crop_catalog c ON c.crop_key = r.crop_name AND c.enabled_for_recommendation = 1
  LEFT JOIN crop_yield_bounds b ON b.crop_key = r.crop_name
)
INSERT INTO crop_yield_observations (source_row_id, crop_key, district, year, hectares, production_mt, yield_kg_per_ha, source_id)
SELECT id, crop_name, normalized_district, year, hectares, production_mt, yield_kg_per_ha, 'crops_db_import'
FROM classified WHERE accepted = 1;

CREATE INDEX idx_observations_crop_district_year ON crop_yield_observations(crop_key, district, year DESC);
CREATE INDEX idx_rejections_reason ON rejected_crop_rows(rejection_reason);

CREATE VIEW recommendation_yields AS
SELECT o.crop_key, c.display_name, o.district, o.year, o.hectares, o.production_mt,
       ROUND(o.yield_kg_per_ha, 2) AS yield_kg_per_ha, o.source_id
FROM crop_yield_observations o JOIN crop_catalog c USING (crop_key)
WHERE c.enabled_for_recommendation = 1;

CREATE VIEW latest_district_yields AS
WITH ranked AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY crop_key, district ORDER BY year DESC) AS row_num
  FROM crop_yield_observations
)
SELECT crop_key, district, year, hectares, production_mt, ROUND(yield_kg_per_ha, 2) AS yield_kg_per_ha, source_id
FROM ranked WHERE row_num = 1;

CREATE VIEW quality_summary AS
SELECT 'accepted' AS status, crop_key AS category, count(*) AS rows FROM crop_yield_observations GROUP BY crop_key
UNION ALL
SELECT 'rejected', rejection_reason, count(*) FROM rejected_crop_rows GROUP BY rejection_reason;

DETACH DATABASE raw;
VACUUM;
