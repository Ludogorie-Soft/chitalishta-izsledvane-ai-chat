-- public.municipalities definition

-- Drop table

-- DROP TABLE public.municipalities;

CREATE TABLE public.municipalities (
	id uuid NOT NULL,
	district varchar(100) NULL,
	district_code varchar(10) NULL,
	migration_coefficient float8 NULL,
	mrrb_category varchar(100) NULL,
	municipality varchar(100) NULL,
	municipality_code varchar(10) NOT NULL,
	municipality_norm varchar(100) NULL,
	nuts1 varchar(10) NULL,
	nuts2 varchar(10) NULL,
	nuts3 varchar(10) NULL,
	population_over_65_aggregate int4 NULL,
	population_under_15_aggregate int4 NULL,
	share_bulgarian float8 NULL,
	share_others float8 NULL,
	share_roma float8 NULL,
	share_turkish float8 NULL,
	total_chitalishta int4 NULL,
	CONSTRAINT municipalities_pkey PRIMARY KEY (id),
	CONSTRAINT uk_94eh03mnpurmukl254shp7mt2 UNIQUE (municipality_code)
);


-- public.municipality_metrics definition

-- Drop table

-- DROP TABLE public.municipality_metrics;

CREATE TABLE public.municipality_metrics (
	id uuid NOT NULL,
	additional_positions float8 NULL,
	average_insurance_income numeric(10, 2) NULL,
	chitalishta_no_training_percent numeric(10, 2) NULL,
	chitalishta_per_10k_residents numeric(10, 1) NULL,
	chitalishta_per_1k_children_under_15 numeric(10, 1) NULL,
	chitalishta_per_1k_elderly numeric(10, 1) NULL,
	chitalishta_per_1k_kindergarten numeric(10, 1) NULL,
	chitalishta_per_1k_students numeric(10, 1) NULL,
	city_chitalishta int4 NULL,
	expenses_for_salaries_percent numeric(10, 2) NULL,
	expenses_other_percent numeric(10, 2) NULL,
	revenue_from_other_percent numeric(10, 2) NULL,
	revenue_from_rent_percent numeric(10, 2) NULL,
	revenue_from_subsidies_percent numeric(10, 2) NULL,
	secretaries_count float8 NULL,
	secretaries_higher_education_percent numeric(10, 2) NULL,
	staff_higher_education_percent numeric(10, 2) NULL,
	staff_secondary_education_percent numeric(10, 2) NULL,
	state_subsidy_amount numeric(15, 2) NULL,
	state_subsidy_per_capita numeric(10, 2) NULL,
	total_chitalishta int4 NULL,
	total_staff float8 NULL,
	unique_employment_contracts int4 NULL,
	village_chitalishta int4 NULL,
	municipality_id uuid NOT NULL,
	CONSTRAINT municipality_metrics_pkey PRIMARY KEY (id),
	CONSTRAINT uk_pllim8m1391nr8ch9vqw4ye1b UNIQUE (municipality_id),
	CONSTRAINT fkqkvhakp2fdtt4p1upg0tnywky FOREIGN KEY (municipality_id) REFERENCES public.municipalities(id)
);


-- public.municipality_year_data definition

-- Drop table

-- DROP TABLE public.municipality_year_data;

CREATE TABLE public.municipality_year_data (
	municipality_code varchar(10) NOT NULL,
	"year" int4 NOT NULL,
	additional_positions float8 NULL,
	average_insurance_income numeric(10, 2) NULL,
	companies_number int4 NULL,
	companies_per_capita float8 NULL,
	employment_rate float8 NULL,
	expenses_salaries_thousands numeric(15, 2) NULL,
	expenses_social_security_thousands numeric(15, 2) NULL,
	gross_value_added_per_person float8 NULL,
	gross_wage_monthly float8 NULL,
	hospitals int4 NULL,
	kids_kindergartens int4 NULL,
	municipality_population int4 NULL,
	poor_health float8 NULL,
	revenue_from_rent_thousands numeric(15, 2) NULL,
	revenue_from_subsidies_thousands numeric(15, 2) NULL,
	secretaries_count float8 NULL,
	secretaries_higher_education_count float8 NULL,
	staff_higher_education_count float8 NULL,
	staff_secondary_education_count float8 NULL,
	students_number int4 NULL,
	students_per_1000 float8 NULL,
	subsidized_positions float8 NULL,
	total_expenses_thousands numeric(15, 2) NULL,
	total_revenue_thousands numeric(15, 2) NULL,
	total_staff_count float8 NULL,
	unemployment_rate float8 NULL,
	unemployment_rate_15_29 float8 NULL,
	unique_employment_contracts int4 NULL,
	urban_population_percent float8 NULL,
	municipality_id uuid NOT NULL,
	CONSTRAINT municipality_year_data_pkey PRIMARY KEY (municipality_code, year),
	CONSTRAINT fk1dxqb8b8nu2ux3jj7ugq6n0d7 FOREIGN KEY (municipality_id) REFERENCES public.municipalities(id)
);


-- public.settlements definition

-- Drop table

-- DROP TABLE public.settlements;

CREATE TABLE public.settlements (
	ekatte varchar(10) NOT NULL,
	elementary_education int4 NULL,
	higher_education int4 NULL,
	illiterate int4 NULL,
	literate int4 NULL,
	no_education int4 NULL,
	population_15_64 int4 NULL,
	population_over_65 int4 NULL,
	population_under_15 int4 NULL,
	primary_education int4 NULL,
	secondary_education int4 NULL,
	settlement_norm varchar(200) NULL,
	settlement_population int4 NULL,
	village_city varchar(20) NULL,
	municipality_code varchar(10) NOT NULL,
	CONSTRAINT settlements_pkey PRIMARY KEY (ekatte),
	CONSTRAINT fkjhg5fnvbqxrlkc1hw9ew2lb7s FOREIGN KEY (municipality_code) REFERENCES public.municipalities(municipality_code)
);


-- public.chitalishta definition

-- Drop table

-- DROP TABLE public.chitalishta;

CREATE TABLE public.chitalishta (
	id uuid NOT NULL,
	address varchar(300) NULL,
	ekatte_code varchar(10) NULL,
	empl_category varchar(50) NULL,
	is_munip_center varchar(10) NULL,
	mayorality_code varchar(10) NULL,
	"name" varchar(200) NULL,
	national_list varchar(500) NULL,
	phone varchar(300) NULL,
	reg_n varchar(50) NOT NULL,
	regional_list varchar(500) NULL,
	settlement_norm varchar(200) NULL,
	slug varchar(255) NULL,
	town varchar(200) NULL,
	uic varchar(50) NULL,
	village_city varchar(20) NULL,
	municipality_id uuid NOT NULL,
	ekatte varchar(10) NULL,
	CONSTRAINT chitalishta_pkey PRIMARY KEY (id),
	CONSTRAINT uk_f6ytk131a4x41almpbpmwrv7m UNIQUE (reg_n),
	CONSTRAINT fkbg902jyab8yqtte1tdxe96oje FOREIGN KEY (ekatte) REFERENCES public.settlements(ekatte),
	CONSTRAINT fko7k4p7p01wn249nnebyycx64m FOREIGN KEY (municipality_id) REFERENCES public.municipalities(id)
);


-- public.chitalishte_year_data definition

-- Drop table

-- DROP TABLE public.chitalishte_year_data;

CREATE TABLE public.chitalishte_year_data (
	reg_n varchar(50) NOT NULL,
	"year" int4 NOT NULL,
	absolute_liquidity numeric(10, 2) NULL,
	accumulated_loss numeric(15, 2) NULL,
	accumulated_profit numeric(15, 2) NULL,
	administrative_positions int4 NULL,
	art_clubs int4 NULL,
	art_clubs_text text NULL,
	asset_profitability numeric(10, 2) NULL,
	assets_per_staff numeric(15, 2) NULL,
	average_annual_staff numeric(10, 2) NULL,
	borrowed_documents int4 NULL,
	cash numeric(15, 2) NULL,
	chairman text NULL,
	classical_dance_groups int4 NULL,
	collaborative_projects int4 NULL,
	computerized_workstations int4 NULL,
	computerized_workstations_alt int4 NULL,
	current_assets numeric(15, 2) NULL,
	dance_groups int4 NULL,
	debt_to_tangible_assets numeric(10, 2) NULL,
	disability_work text NULL,
	equity numeric(15, 2) NULL,
	equity_profitability numeric(10, 2) NULL,
	event_participations int4 NULL,
	external_services_spending numeric(15, 2) NULL,
	fast_liquidity numeric(10, 2) NULL,
	financial_autonomy numeric(10, 2) NULL,
	financial_debt numeric(10, 2) NULL,
	fixed_assets numeric(15, 2) NULL,
	folklore_groups int4 NULL,
	home_visits int4 NULL,
	immediate_liquidity numeric(10, 2) NULL,
	imposed_sanctions int4 NULL,
	income_per_staff numeric(15, 2) NULL,
	income_profitability numeric(10, 2) NULL,
	independent_projects int4 NULL,
	intangible_assets numeric(15, 2) NULL,
	international_projects int4 NULL,
	internet_access int4 NULL,
	investment numeric(15, 2) NULL,
	language_schools int4 NULL,
	language_schools_text text NULL,
	liabilities numeric(15, 2) NULL,
	liabilities_per_staff numeric(15, 2) NULL,
	library_activity text NULL,
	library_staff_higher_edu int4 NULL,
	library_staff_secondary_edu int4 NULL,
	library_staff_total int4 NULL,
	library_staff_training int4 NULL,
	library_units int4 NULL,
	library_users int4 NULL,
	library_users_online int4 NULL,
	local_history_clubs int4 NULL,
	local_history_clubs_text text NULL,
	long_term_liabilities numeric(15, 2) NULL,
	loss numeric(15, 2) NULL,
	material_reserves numeric(15, 2) NULL,
	membership_applications int4 NULL,
	museum_collections int4 NULL,
	museum_collections_text text NULL,
	national_projects int4 NULL,
	net_income numeric(15, 2) NULL,
	new_members int4 NULL,
	newly_acquired int4 NULL,
	newly_acquired_alt int4 NULL,
	operating_income numeric(15, 2) NULL,
	other_activities text NULL,
	other_clubs int4 NULL,
	phone_registry text NULL,
	profit numeric(15, 2) NULL,
	profit_per_staff numeric(15, 2) NULL,
	reading_room_visits int4 NULL,
	receivables numeric(15, 2) NULL,
	regional_projects int4 NULL,
	rejected_applications int4 NULL,
	secretary text NULL,
	short_term_liabilities numeric(15, 2) NULL,
	short_term_liquidity numeric(10, 2) NULL,
	specialized_positions int4 NULL,
	staff_count int4 NULL,
	staff_expenses numeric(15, 2) NULL,
	staff_higher_edu int4 NULL,
	status varchar(100) NULL,
	subsidized_staff_count int4 NULL,
	support_staff int4 NULL,
	theater_groups int4 NULL,
	total_assets numeric(15, 2) NULL,
	total_expenditure numeric(15, 2) NULL,
	total_income numeric(15, 2) NULL,
	total_members int4 NULL,
	total_staff_registry int4 NULL,
	trade_price numeric(15, 2) NULL,
	training_participation int4 NULL,
	turnover_count numeric(10, 2) NULL,
	turnover_time numeric(10, 2) NULL,
	vocal_groups int4 NULL,
	chitalishte_id uuid NOT NULL,
	CONSTRAINT chitalishte_year_data_pkey PRIMARY KEY (reg_n, year),
	CONSTRAINT fkfew64t7lnlwo1atbnflsh63da FOREIGN KEY (chitalishte_id) REFERENCES public.chitalishta(id)
);