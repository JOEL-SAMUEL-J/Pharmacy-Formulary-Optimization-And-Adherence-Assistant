-- Plans
CREATE TABLE plans (
    contract_id VARCHAR(5) NOT NULL,
    plan_id VARCHAR(3) NOT NULL,
    segment_id VARCHAR(3) NOT NULL,
    plan_name VARCHAR(255),
    formulary_id VARCHAR(8) NOT NULL,

    PRIMARY KEY (
        contract_id,
        plan_id,
        segment_id
    ),

    INDEX idx_plans_formulary (
        formulary_id
    )
);

-- Formulary Drugs
CREATE TABLE formulary_drugs (
    formulary_id VARCHAR(8) NOT NULL,
    formulary_version VARCHAR(5),
    contract_year VARCHAR(4),

    rxcui VARCHAR(20) NOT NULL,
    ndc VARCHAR(11) NOT NULL,

    tier VARCHAR(2) NOT NULL,

    quantity_limit_yn CHAR(1),
    quantity_limit_amount VARCHAR(20),
    quantity_limit_days VARCHAR(10),

    prior_authorization_yn CHAR(1),
    step_therapy_yn CHAR(1),

    PRIMARY KEY (
        formulary_id,
        rxcui,
        ndc
    ),

    INDEX idx_formulary_rxcui (
        formulary_id,
        rxcui
    ),

    INDEX idx_rxcui (
        rxcui
    )
);

-- Beneficiary Costs
CREATE TABLE beneficiary_costs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    contract_id VARCHAR(5) NOT NULL,
    plan_id VARCHAR(3) NOT NULL,
    segment_id VARCHAR(3) NOT NULL,

    coverage_level VARCHAR(1) NOT NULL,
    tier VARCHAR(2) NOT NULL,
    days_supply VARCHAR(1) NOT NULL,

    cost_type_pref VARCHAR(1),
    cost_amt_pref DECIMAL(12, 4),

    cost_type_nonpref VARCHAR(1),
    cost_amt_nonpref DECIMAL(12, 4),

    cost_type_mail_pref VARCHAR(1),
    cost_amt_mail_pref DECIMAL(12, 4),

    cost_type_mail_nonpref VARCHAR(1),
    cost_amt_mail_nonpref DECIMAL(12, 4),

    tier_specialty_yn CHAR(1),
    ded_applies_yn CHAR(1),

    UNIQUE KEY uq_beneficiary_cost (
        contract_id,
        plan_id,
        segment_id,
        tier,
        coverage_level,
        days_supply
    ),

    INDEX idx_cost_lookup (
        contract_id,
        plan_id,
        segment_id,
        tier
    )
);