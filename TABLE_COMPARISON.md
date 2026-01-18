# Table Comparison: Old vs New Schema

## Summary

There are **TWO different sets of tables** in the database:

### Old Schema (Existing Models)
- `chitalishte` - INTEGER id, registration_number
- `information_card` - INTEGER id, chitalishte_id (INTEGER FK)

### New Schema (From SQL Provided)
- `chitalishta` - UUID id, reg_n, municipality_id (UUID FK)
- `chitalishte_year_data` - reg_n + year (composite PK), chitalishte_id (UUID FK)

These are **completely different tables** with different structures and purposes.

---

## Detailed Comparison

### 1. chitalishte (OLD) vs chitalishta (NEW)

#### chitalishte (OLD - Existing Model)
- **Primary Key**: `id` (INTEGER, autoincrement)
- **Unique**: `registration_number` (INTEGER)
- **Columns**:
  - `registration_number` (INTEGER)
  - `created_at` (TIMESTAMP)
  - `address` (VARCHAR 255)
  - `bulstat` (VARCHAR 255)
  - `chairman` (VARCHAR 255)
  - `chitalishta_url` (VARCHAR 255)
  - `email` (VARCHAR 255)
  - `municipality` (VARCHAR 255) - **STRING, not FK**
  - `name` (VARCHAR 255)
  - `phone` (VARCHAR 255)
  - `region` (VARCHAR 255)
  - `secretary` (VARCHAR 255)
  - `status` (VARCHAR 255)
  - `town` (VARCHAR 255)
  - `url_to_libraries_site` (VARCHAR 255)

#### chitalishta (NEW - From SQL Schema)
- **Primary Key**: `id` (UUID)
- **Unique**: `reg_n` (VARCHAR 50)
- **Foreign Keys**:
  - `municipality_id` → `municipalities.id` (UUID)
  - `ekatte` → `settlements.ekatte` (VARCHAR 10)
- **Columns**:
  - `address` (VARCHAR 300) - **Different length**
  - `ekatte_code` (VARCHAR 10) - **NEW**
  - `empl_category` (VARCHAR 50) - **NEW**
  - `is_munip_center` (VARCHAR 10) - **NEW**
  - `mayorality_code` (VARCHAR 10) - **NEW**
  - `name` (VARCHAR 200) - **Different length**
  - `national_list` (VARCHAR 500) - **NEW**
  - `phone` (VARCHAR 300) - **Different length**
  - `reg_n` (VARCHAR 50) - **NEW, replaces registration_number**
  - `regional_list` (VARCHAR 500) - **NEW**
  - `settlement_norm` (VARCHAR 200) - **NEW**
  - `slug` (VARCHAR 255) - **NEW**
  - `town` (VARCHAR 200) - **Different length**
  - `uic` (VARCHAR 50) - **NEW**
  - `village_city` (VARCHAR 20) - **NEW**
  - `municipality_id` (UUID FK) - **NEW, replaces municipality string**
  - `ekatte` (VARCHAR 10 FK) - **NEW**

**Key Differences:**
- Different primary key type (INTEGER vs UUID)
- Different identifier (`registration_number` vs `reg_n`)
- New table has foreign keys to municipalities and settlements
- Many new columns in the new table
- Some columns have different lengths
- Old table has `bulstat`, `chairman`, `chitalishta_url`, `email`, `region`, `secretary`, `status`, `url_to_libraries_site` which are NOT in new table
- New table has many columns NOT in old table

---

### 2. information_card (OLD) vs chitalishte_year_data (NEW)

#### information_card (OLD - Existing Model)
- **Primary Key**: `id` (INTEGER, autoincrement)
- **Foreign Key**: `chitalishte_id` (INTEGER) → `chitalishte.id`
- **Columns**:
  - `chitalishte_id` (INTEGER FK)
  - `year` (INTEGER)
  - `created_at` (TIMESTAMP)
  - `administrative_positions` (INTEGER)
  - `amateur_arts` (INTEGER)
  - `dancing_groups` (INTEGER)
  - `disabilities_and_volunteers` (INTEGER)
  - `employees_count` (DOUBLE)
  - `employees_specialized` (INTEGER)
  - `employees_with_higher_education` (INTEGER)
  - `folklore_formations` (INTEGER)
  - `kraeznanie_clubs` (INTEGER)
  - `language_courses` (INTEGER)
  - `library_activity` (INTEGER)
  - `membership_applications` (INTEGER)
  - `modern_ballet` (INTEGER)
  - `museum_collections` (INTEGER)
  - `new_members` (INTEGER)
  - `other_activities` (INTEGER)
  - `other_clubs` (INTEGER)
  - `participation_in_events` (INTEGER)
  - `participation_in_live_human_treasures_national` (INTEGER)
  - `participation_in_live_human_treasures_regional` (INTEGER)
  - `participation_in_trainings` (INTEGER)
  - `projects_participation_leading` (INTEGER)
  - `projects_participation_partner` (INTEGER)
  - `reg_number` (INTEGER)
  - `registration_number` (INTEGER)
  - `rejected_members` (INTEGER)
  - `subsidiary_count` (DOUBLE)
  - `supporting_employees` (INTEGER)
  - `theatre_formations` (INTEGER)
  - `total_members_count` (INTEGER)
  - `town_population` (INTEGER)
  - `town_users` (INTEGER)
  - `vocal_groups` (INTEGER)
  - `workshops_clubs_arts` (INTEGER)
  - `has_pc_and_internet_services` (BOOLEAN)
  - `bulstat` (VARCHAR 255)
  - `email` (VARCHAR 255)
  - `kraeznanie_clubs_text` (TEXT)
  - `language_courses_text` (TEXT)
  - `museum_collections_text` (TEXT)
  - `sanctions_for31and33` (VARCHAR 255)
  - `url` (VARCHAR 255)
  - `webpage` (VARCHAR 255)
  - `workshops_clubs_arts_text` (TEXT)

#### chitalishte_year_data (NEW - From SQL Schema)
- **Primary Key**: Composite (`reg_n` VARCHAR 50, `year` INTEGER)
- **Foreign Key**: `chitalishte_id` (UUID) → `chitalishta.id`
- **Columns**: (Many more columns - 100+ fields including financial data, library data, etc.)

**Key Differences:**
- Different primary key structure (single INTEGER id vs composite reg_n + year)
- Different foreign key type (INTEGER vs UUID)
- New table has MANY more columns (100+ vs ~50)
- New table includes financial data (assets, liabilities, income, expenses, etc.)
- New table includes more detailed library data
- New table includes more detailed project data
- Some column names are similar but many are different
- New table uses `reg_n` instead of `chitalishte_id` as part of primary key

---

## Column Name Mapping (Similar Columns)

### Similar but Different:
- `information_card.administrative_positions` ≈ `chitalishte_year_data.administrative_positions` ✅
- `information_card.new_members` ≈ `chitalishte_year_data.new_members` ✅
- `information_card.total_members_count` ≈ `chitalishte_year_data.total_members` ⚠️ (different name)
- `information_card.membership_applications` ≈ `chitalishte_year_data.membership_applications` ✅
- `information_card.rejected_members` ≈ `chitalishte_year_data.rejected_applications` ⚠️ (different name)
- `information_card.vocal_groups` ≈ `chitalishte_year_data.vocal_groups` ✅
- `information_card.folklore_formations` ≈ `chitalishte_year_data.folklore_groups` ⚠️ (different name)
- `information_card.theatre_formations` ≈ `chitalishte_year_data.theater_groups` ⚠️ (different name)
- `information_card.dancing_groups` ≈ `chitalishte_year_data.dance_groups` ⚠️ (different name)
- `information_card.language_courses` ≈ `chitalishte_year_data.language_schools` ⚠️ (different name)
- `information_card.museum_collections` ≈ `chitalishte_year_data.museum_collections` ✅
- `information_card.participation_in_events` ≈ `chitalishte_year_data.event_participations` ⚠️ (different name)
- `information_card.participation_in_trainings` ≈ `chitalishte_year_data.training_participation` ⚠️ (different name)
- `information_card.projects_participation_leading` ≈ `chitalishte_year_data.independent_projects` ⚠️ (different name)
- `information_card.projects_participation_partner` ≈ `chitalishte_year_data.collaborative_projects` ⚠️ (different name)

### Columns Only in OLD (information_card):
- `subsidiary_count` - NOT in new table
- `employees_count` - NOT in new table (but has `staff_count`)
- `employees_specialized` - NOT in new table (but has `specialized_positions`)
- `employees_with_higher_education` - NOT in new table (but has `staff_higher_edu`)
- `town_population` - NOT in new table
- `town_users` - NOT in new table
- `has_pc_and_internet_services` - NOT in new table (but has `internet_access`)

### Columns Only in NEW (chitalishte_year_data):
- Financial columns: `absolute_liquidity`, `accumulated_loss`, `accumulated_profit`, `asset_profitability`, `assets_per_staff`, `cash`, `current_assets`, `debt_to_tangible_assets`, `equity`, `equity_profitability`, `financial_autonomy`, `financial_debt`, `fixed_assets`, `income_per_staff`, `income_profitability`, `intangible_assets`, `investment`, `liabilities`, `liabilities_per_staff`, `long_term_liabilities`, `loss`, `material_reserves`, `net_income`, `operating_income`, `profit`, `profit_per_staff`, `receivables`, `short_term_liabilities`, `total_assets`, `total_expenditure`, `total_income`, `trade_price`
- Library columns: `borrowed_documents`, `library_staff_higher_edu`, `library_staff_secondary_edu`, `library_staff_total`, `library_staff_training`, `library_units`, `library_users`, `library_users_online`, `reading_room_visits`, `turnover_count`, `turnover_time`
- Project columns: `national_projects`, `regional_projects`, `international_projects`
- Other: `classical_dance_groups`, `computerized_workstations`, `computerized_workstations_alt`, `home_visits`, `imposed_sanctions`, `newly_acquired`, `newly_acquired_alt`, `phone_registry`, `subsidized_staff_count`, `support_staff`, `total_staff_registry`, `average_annual_staff`, `staff_expenses`

---

## Conclusion

These are **completely different table structures**. The new schema (`chitalishta` and `chitalishte_year_data`) is much more comprehensive and includes:
1. Proper foreign key relationships to municipalities and settlements
2. Financial data (assets, liabilities, income, expenses)
3. More detailed library statistics
4. More detailed project information
5. UUID-based primary keys instead of INTEGER

The old schema (`chitalishte` and `information_card`) appears to be a simpler, legacy structure.

**Recommendation**: Both sets of tables can coexist in the database, but you'll need to decide which one to use for the SQL agent queries, or support both.
