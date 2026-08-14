# CMS Raw Data

This directory contains the **raw CMS source files** used by the
Pharmacy Formulary Optimization and Adherence Assistant.

The files are kept in their original/raw form and serve as the source
data for the project's cleaning, validation, transformation, database
loading, and rule-based optimization pipeline.

> **Important:** Raw CMS files should not be modified directly.
> Processed and transformed data should be stored separately.

------------------------------------------------------------------------

## 1. Role of the CMS Raw Data

The raw CMS datasets provide the information required to resolve:

``` text
Service Area
      ↓
Plan / Segment
      ↓
Formulary
      ↓
Drug
      ↓
Tier / PA / ST / QL
      ↓
Coverage Phase + Days Supply
      ↓
Cost Sharing
      ↓
Optimization Analysis
```

The system does not evaluate a drug independently.

Instead, it evaluates a:

``` text
Service Area + Plan + Drug + Coverage Phase + Days Supply
```

combination.

------------------------------------------------------------------------

## 2. Raw CMS Files

The `raw` directory contains the following source files:

``` text
raw/
├── .gitkeep
├── basic_drugs_formulary_file.txt
├── beneficiary_cost_file.txt
├── excluded_drugs_formulary_file.txt
├── geographic_locator_file.txt
├── Indication_Based_Coverage_Formulary_File.txt
├── insulin_beneficiary_cost_file.txt
└── plan_information_file.txt
```

------------------------------------------------------------------------

## 3. Dataset Responsibilities

### 3.1 Plan Information

**File:**

``` text
plan_information_file.txt
```

This is one of the most important datasets because the application
begins with a user-selected **Plan**.

The user sees:

``` text
PLAN_NAME
```

The backend resolves the selected plan to:

``` text
CONTRACT_ID
PLAN_ID
SEGMENT_ID
```

The plan information is then used to determine the applicable:

``` text
FORMULARY_ID
VERSION
```

The relationship is:

``` text
PLAN_NAME
    ↓
CONTRACT_ID + PLAN_ID + SEGMENT_ID
    ↓
FORMULARY_ID + VERSION
```

This allows the system to establish:

``` text
Plan → Formulary
```

before looking up the selected drug.

### Why it matters

Without the plan information, the system cannot reliably determine which
formulary should be applied to a user's selected plan.

------------------------------------------------------------------------

### 3.2 Geographic Locator

**File:**

``` text
geographic_locator_file.txt
```

This dataset supports the **Service Area** part of the architecture.

The project does not assume that County is always the parent of a plan
because different plan types use different geographic identifiers.

Conceptually:

``` text
Service Area
     ↓
Plan / Segment
```

The relevant geographic identifier depends on plan type:

  Plan Type        Geographic Identifier
  ---------------- -----------------------
  Local MA         `COUNTY_CODE`
  Regional MA      `MA_REGION_CODE`
  Standalone PDP   `PDP_REGION_CODE`

Therefore, geographic information is used to validate whether the
selected plan is applicable within the selected Service Area.

------------------------------------------------------------------------

### 3.3 Basic Drugs Formulary

**File:**

``` text
basic_drugs_formulary_file.txt
```

This dataset provides drug-level formulary and access information.

It is used to determine information such as:

``` text
Drug
Tier
Prior Authorization (PA)
Step Therapy (ST)
Quantity Limits (QL)
```

The main purpose is **Access Analysis**.

Conceptually:

``` text
Formulary
    ↓
Drug
    ↓
Tier + PA + ST + QL
```

These fields help identify potential access barriers associated with a
drug under the selected plan's formulary.

------------------------------------------------------------------------

### 3.4 Beneficiary Cost

**File:**

``` text
beneficiary_cost_file.txt
```

This dataset provides plan-listed beneficiary cost-sharing information.

It supports:

-   Affordability Analysis
-   Channel Analysis
-   Coverage-phase-specific cost lookup
-   Days-supply-specific cost lookup

Relevant information includes:

``` text
CONTRACT_ID
PLAN_ID
SEGMENT_ID
COVERAGE_LEVEL
TIER
DAYS_SUPPLY
COST_TYPE
COST_AMOUNT
Preferred Retail
Standard Retail
Mail
```

The applicable cost-sharing record is resolved using the relevant
plan/segment, tier, coverage phase, and days supply.

Conceptually:

``` text
Plan / Segment
      +
Tier
      +
Coverage Level
      +
Days Supply
      ↓
Applicable Cost Sharing
```

------------------------------------------------------------------------

### 3.5 Excluded Drugs Formulary

**File:**

``` text
excluded_drugs_formulary_file.txt
```

This dataset contains information about drugs that are excluded from
coverage.

It is maintained as a separate formulary-related source and can be used
when exclusion analysis is required.

------------------------------------------------------------------------

### 3.6 Indication-Based Coverage Formulary

**File:**

``` text
Indication_Based_Coverage_Formulary_File.txt
```

This dataset contains coverage information where coverage may depend on
the indication associated with a drug.

It provides additional coverage context for cases where indication-based
rules apply.

------------------------------------------------------------------------

### 3.7 Insulin Beneficiary Cost

**File:**

``` text
insulin_beneficiary_cost_file.txt
```

This dataset provides beneficiary cost information specific to insulin
products and insulin-related coverage.

It can be used when the selected drug falls under the applicable insulin
cost-sharing rules.

------------------------------------------------------------------------

## 4. How the Raw Datasets Work Together

The main relationships are:

``` text
                  SERVICE AREA
                       ↓
                PLAN / SEGMENT
                       ↓
               PLAN INFORMATION
                       ↓
                 FORMULARY
                       ↓
                     DRUG
                       ↓
          BASIC DRUGS FORMULARY
                       ↓
             Tier / PA / ST / QL
                       ↓
          ┌────────────┴────────────┐
          ↓                         ↓
   COVERAGE PHASE              DAYS SUPPLY
          ↓                         ↓
          └────────────┬────────────┘
                       ↓
              BENEFICIARY COST
                       ↓
              COST SHARING
                       ↓
            OPTIMIZATION ANALYSIS
```

The datasets therefore have different responsibilities rather than being
treated as interchangeable sources.

------------------------------------------------------------------------

## 5. User Input to CMS Data Mapping

The application is designed around five primary user inputs:

``` text
Service Area
Plan
Drug
Coverage Phase
Days Supply
```

These map to CMS data as follows:

  User Input              CMS Data / Concept
  ----------------------- --------------------------------------
  Service Area            Geographic/service-area information
  Plan                    `PLAN_NAME`
  Plan backend identity   `CONTRACT_ID + PLAN_ID + SEGMENT_ID`
  Formulary               `FORMULARY_ID + VERSION`
  Drug                    Drug/formulary record
  Coverage Phase          `COVERAGE_LEVEL`
  Days Supply             `DAYS_SUPPLY`

------------------------------------------------------------------------

## 6. Coverage Phase

Coverage Phase is represented by:

``` text
COVERAGE_LEVEL
```

in the Beneficiary Cost data.

The current mapping is:

    `COVERAGE_LEVEL` Meaning
  ------------------ ------------------
                 `0` Pre-deductible
                 `1` Initial coverage
                 `3` Catastrophic

For example:

``` text
User selects:
Initial Coverage

System uses:
COVERAGE_LEVEL = 1
```

Coverage Phase answers:

> At what point in the beneficiary's coverage does this cost-sharing
> rule apply?

------------------------------------------------------------------------

## 7. Days Supply

Days Supply is represented by:

``` text
DAYS_SUPPLY
```

in the Beneficiary Cost data.

The current mapping is:

    `DAYS_SUPPLY` Meaning
  --------------- ---------
              `1` 30 days
              `2` 90 days
              `3` Other
              `4` 60 days

For example:

``` text
User selects:
30 days

System uses:
DAYS_SUPPLY = 1
```

Days Supply answers:

> For what prescription duration does this cost-sharing rule apply?

------------------------------------------------------------------------

## 8. Cost-Sharing Lookup

Coverage Phase and Days Supply are primarily important for retrieving
the correct cost-sharing record.

The conceptual lookup is:

``` text
CONTRACT_ID
+
PLAN_ID
+
SEGMENT_ID
+
TIER
+
COVERAGE_LEVEL
+
DAYS_SUPPLY
        ↓
Applicable Cost-Sharing Record
```

For example:

``` text
Plan A
Drug X
Tier 3
Initial Coverage
30 Days
        ↓
COVERAGE_LEVEL = 1
DAYS_SUPPLY = 1
        ↓
Applicable Cost Sharing
```

This ensures the system does not use a cost-sharing record from the
wrong coverage phase or prescription duration.

------------------------------------------------------------------------

## 9. End-to-End CMS Data Resolution

The application uses the raw CMS data in the following order:

``` text
USER INPUT
────────────────────────────────

Service Area
Plan Name
Drug
Coverage Phase
Days Supply

                ↓

VALIDATE PLAN IN SERVICE AREA

                ↓

RESOLVE PLAN

PLAN_NAME
    ↓
CONTRACT_ID
PLAN_ID
SEGMENT_ID

                ↓

RESOLVE FORMULARY

FORMULARY_ID
VERSION

                ↓

FIND DRUG IN FORMULARY

                ↓

RESOLVE ACCESS INFORMATION

Tier
Prior Authorization
Step Therapy
Quantity Limits

                ↓

RESOLVE COST CONTEXT

COVERAGE_LEVEL
DAYS_SUPPLY

                ↓

RETRIEVE COST SHARING

                ↓

OPTIMIZATION ANALYSIS

                ↓

EXPLAINABLE OPTIMIZATION OPPORTUNITY

                ↓

PRIORITY SCORE
```

------------------------------------------------------------------------

## 10. CMS Raw Data Processing Pipeline

The raw CMS files move through the project's data pipeline:

``` text
CMS Raw Files
      ↓
Pandas
      ↓
Clean
      ↓
Validate
      ↓
Transform
      ↓
MySQL
      ↓
FastAPI
      ↓
Rule Engine
      ↓
React UI
```

### Pandas

Used to:

-   Read the raw CMS files
-   Handle delimiters and encodings
-   Clean data
-   Validate records
-   Transform fields
-   Prepare data for database loading

### MySQL

Stores the cleaned and transformed data in a structured format for
application use.

### FastAPI

Uses the database to resolve:

``` text
Service Area
→ Plan
→ Formulary
→ Drug
→ Access
→ Cost
```

and exposes the results to the frontend.

### Rule Engine

Combines access, affordability, and channel information to identify
potential optimization opportunities.

### React

Provides the interface through which users select the required inputs
and view the resulting analysis.

------------------------------------------------------------------------

## 11. Data Processing Rules

The raw CMS files should follow these principles:

1.  **Do not modify raw source files directly.**
2.  Read raw files using Pandas.
3.  Preserve the original source data.
4.  Validate required identifiers and relationships.
5.  Clean and normalize values where required.
6.  Transform the data into database-ready structures.
7.  Store processed data separately from raw data.
8.  Load validated data into MySQL.
9.  Use the database as the application's primary data source.

------------------------------------------------------------------------

## 12. Why the Raw Data Is Important

The raw CMS datasets provide the foundation for answering:

-   Where does the plan apply?
-   Which plan/segment did the user select?
-   Which formulary is associated with that plan?
-   Is the selected drug present in the formulary?
-   What tier is the drug assigned?
-   Is prior authorization required?
-   Is step therapy required?
-   Are quantity limits present?
-   Which coverage phase applies?
-   Which days supply applies?
-   What cost-sharing record matches the selected context?
-   What retail or mail channel information is available?
-   Does the combination present a potential optimization opportunity?

------------------------------------------------------------------------

## 13. Scope of the CMS Raw Data Layer

The raw data layer is responsible for **providing source information**,
not making the final optimization decision.

The responsibility is separated as follows:

``` text
CMS Raw Data
      ↓
Source Facts
      ↓
Database
      ↓
Application Logic
      ↓
Rule Engine
      ↓
Optimization Opportunity
```

The CMS files provide the facts.

The rule engine interprets those facts according to the project's
defined business rules.

------------------------------------------------------------------------

## 14. Final Architecture

The complete project can be summarized as:

``` text
                    USER
                     │
                     ▼
        Service Area + Plan + Drug
        + Coverage Phase + Days Supply
                     │
                     ▼
              VALIDATION
                     │
                     ▼
             PLAN INFORMATION
                     │
                     ▼
              PLAN / SEGMENT
                     │
                     ▼
                FORMULARY
                     │
                     ▼
                   DRUG
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
 BASIC DRUGS FORMULARY    BENEFICIARY COST
          │                     │
          ▼                     ▼
 Tier / PA / ST / QL    Coverage + Days Supply
          │                     │
          └──────────┬──────────┘
                     ▼
             OPTIMIZATION RULES
                     │
                     ▼
         EXPLAINABLE OPPORTUNITY
                     │
                     ▼
              LOW / MODERATE / HIGH
```

## Core Principle

> **The CMS raw data layer provides the source information needed to
> resolve the user's Service Area → Plan/Segment → Formulary → Drug
> context, determine drug access restrictions, retrieve the correct
> coverage-phase and days-supply cost sharing, and provide the facts
> required by the rule engine to generate an explainable optimization
> opportunity.**
