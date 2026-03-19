# MEDMAP — PROMPT UNIQUE COMPLET
### START Hack 2026 — Track epaCC
### ⚠️ MIS À JOUR POST-BRIEFING DISCORD (19 mars 2026)
### 🔗 Fusion de MEDMAP_PROMPT.md + PROMPT_BACKEND.md + PROMPT_FRONTEND_REACT.md + RESUME_PROJET.md

---

## TABLE DES MATIÈRES

1. [Contexte & Vue d'ensemble](#contexte)
2. [Mises à jour Discord (19 mars)](#discord)
3. [Architecture globale](#architecture)
4. [Contrat partagé (contracts.py / contracts.ts)](#contrat)
5. [Backend — Pipeline](#pipeline)
   - Module 1 : Ingestion
   - Module 2 : Validation & Nettoyage
   - Module 3 : Mapping
   - Module 4 : NLP (bonus)
   - Module 5 : Anomaly Detection (bonus)
   - Module 6 : Export SQL
   - Module 7 : Agents (bonus)
   - Module 8 : Configuration
6. [Backend — API FastAPI (25 endpoints)](#api)
7. [Frontend — Spec complète (9 pages)](#frontend)
8. [Features bonus (1-11)](#bonus)
9. [Requirements, Docker, Variables d'env](#infra)
10. [Contraintes](#contraintes)
11. [Ordre d'implémentation](#ordre)

---

<a name="contexte"></a>

## 1. CONTEXTE & VUE D'ENSEMBLE

MEDMAP est une app de **Smart Health Data Mapping** pour le hackathon START Hack 2026 (track epaCC).

Elle ingère **8 sources de données médicales hétérogènes** + **28 fichiers split** (4 cliniques × 7 types), les nettoie automatiquement, les mappe vers un schéma SQL cible en **7 tables**, et expose un **dashboard interactif** avec alertes cliniques, qualité des données, et correction manuelle.

Le tout doit tourner **100% offline** (on-premises). Les features LLM (Ask Your Data, SBAR, Auto-Doc) ont un fallback offline.

Repo GitHub de référence : `github.com/adriank71/epaCC-START-Hack-2026`
Le dossier `DB/` contient `CreateImportTables.sql` avec le schéma SQL cible exact.
`DB/Hack2026.bak` (3.65 MB) = backup SQL Server avec données d'exemple.

### Les 8 sources de données

1. `synth_labs_1000_cases.csv` et `.xlsx` — résultats labo (~1000 cas, 64 colonnes)
2. `synthetic_cases_icd10_ops.csv` — codes diagnostics (50 cas)
3. `synthetic_device_motion_fall_data.csv` — capteurs mouvement (~24K lignes)
4. `synthetic_device_raw_1hz_motion_fall.csv` — capteurs 1Hz (~108K lignes, 9.99MB)
5. `synthetic_medication_raw_inpatient.csv` — médicaments (~14K lignes)
6. `synthetic_nursing_daily_reports_en.csv` — notes infirmières (182 notes)
7. `epaAC-Data-1 à 5` — assessments epaCC (900+ colonnes, allemand)
8. `IID-SID-ITEM.csv` — dictionnaire de décodage SAP

### Qui fait quoi ?

| Rôle | Dossier | Stack | Travail |
|------|---------|-------|---------|
| **Dev Backend** | `medmap/` | Python 3.11, FastAPI, pandas, SQLite | Pipeline complet + API 25 endpoints + 7 agents IA |
| **Dev Frontend** | `frontend/` | Next.js 16, TypeScript, Tailwind, shadcn/ui | Dashboard 9 pages basé sur starter shadcn |

Les deux se connectent via REST API JSON. Aucun fichier en commun → git merge sans conflits.

---

<a name="discord"></a>

## 2. MISES À JOUR IMPORTANTES (Discord + vérification repo 19 mars 2026)

### 2.1 Structure des dossiers — correction complète
- Dossier **avec erreurs** → données INPUT à nettoyer
- Dossier **sans erreurs** → données de VALIDATION (comparer votre output avec ces données)
- Dossier **split_data_pat_case_altered/** → LE VRAI DÉFI : données de **4 cliniques différentes** en formats mixtes (CSV, XLSX, PDF)
- **DB/Hack2026.bak** (3.65 MB) → backup SQL Server complet. Restaurer via `CreateDatabase.cmd`

### 2.2 🚨 Dossier split = 4 cliniques × 7 types = 28 fichiers
```
split_data_pat_case_altered/
├── clinic_1_labs.csv
├── clinic_1_device.csv
├── clinic_1_device_1hz.csv
├── clinic_1_icd_ops.csv
├── clinic_1_medication.csv
├── clinic_1_nursing.csv
├── clinic_1_epaAC-Data.csv
├── clinic_2_... (×7 fichiers)
├── clinic_3_... (×7 fichiers)
└── clinic_4_labs.csv
    clinic_4_device.csv
    clinic_4_medication.csv
    clinic_4_icd_ops.csv
    clinic_4_epaAC-Data.xlsx   ← XLSX (pas CSV)
    clinic_4_nursing.pdf        ← 🚨 PDF ! Besoin de pdfplumber
    clinic_4_device_1hz.csv
```
**L'ingestion doit gérer CSV + XLSX + PDF en input.**

### 2.3 🚨 PDF en input
`clinic_4_nursing.pdf` contient des notes infirmières en PDF.
Ajouter `pdfplumber` dans requirements.txt et dans ingestion.py.

### 2.4 PID dupliqués entre sources — stratégie officielle
Même PID qui pointe vers des données différentes (genre M/F) = erreur intentionnelle.
- **Option A** (priorité) : Ajouter préfixe source → `LAB_123456`, `MOT_123456`, `EPA_123456`
- **Option B** : Afficher comme erreur d'import dans le dashboard

### 2.5 ⚠️ Analyse patient NON OBLIGATOIRE
Citation officielle : **"You don't need to do analysis about patient condition"**
→ NLP, anomaly detection, SBAR, clinical reasoner = **FEATURES BONUS uniquement**
→ Le cœur obligatoire : ingestion → nettoyage → mapping → import DB → dashboard qualité

### 2.6 IID-SID-ITEM.csv — décodeur de codes SAP epaAC
Colonnes : `ItmIID` (ex: E0_I_00) | `ItmSID` (ex: 00_01) | `ItmName255_DE` | `ItmName255_EN`
⚠️ **Erreur de quoting ligne 4481** → parser avec `on_bad_lines='skip'` ou `error_bad_lines=False`

### 2.7 🚨 Deux formats epaAC COMPLÈTEMENT DIFFÉRENTS
- **Clean** (epaAC-Data-1 à 5) → codes SAP : `EPA0001`, `PATGEB`, `MANDT`, `EPAST0BTS`...
- **Dirty** (epaAC-Data-3 uniquement) → allemand : `Körpergröße`, `BMI`, `AufnDat`...
- **Split** (clinic_X_epaAC) → peut varier par clinique
- Utiliser IID-SID-ITEM.csv pour décoder les codes SAP vers les noms lisibles.
- ⚠️ Dans le dirty folder, il y a seulement **1 fichier epaAC** (Data-3), pas 5.

### 2.8 Noms de fichiers différents clean vs dirty
| Clean                              | Dirty                          |
|------------------------------------|--------------------------------|
| synth_labs_**1000_cases**.csv      | synth_labs.csv                 |
| synthetic_**device_motion_fall_data**.csv | synth_device_motion_fall.csv |
| synthetic_device_**raw_1hz_motion_fall**.csv | synth_device_raw_1hz_motion_fall.csv |
**Détecter par contenu/colonnes, pas par nom de fichier.**

### 2.9 Mapping sans case_id — règle officielle (Lena Frischen)
Si un fichier n'a pas de case_id direct :
→ Utiliser **patient_id + datetime** pour mapper vers le bon cas dans tbCaseData.

---

<a name="architecture"></a>

## 3. ARCHITECTURE GLOBALE

```
start_hack/
├── MEDMAP_PROMPT.md              ← CE FICHIER (prompt unique)
│
├── medmap/                       ← DOSSIER BACKEND
│   ├── contracts.py              ← CONTRAT PARTAGÉ (déjà créé)
│   ├── api/                      ← API FastAPI
│   │   ├── __init__.py
│   │   ├── main.py               ← App FastAPI + CORS
│   │   ├── dependencies.py       ← DB connection partagée
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── pipeline.py
│   │       ├── upload.py
│   │       ├── overview.py
│   │       ├── agents.py
│   │       ├── patients.py
│   │       ├── alerts.py
│   │       ├── quality.py
│   │       ├── ask.py
│   │       └── corrections.py
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── ingestion.py          ← Lecture multi-format
│   │   ├── validator.py          ← Règles de validation clinique
│   │   ├── cleaner.py            ← Nettoyage et normalisation
│   │   ├── mapper.py             ← Mapping colonnes → schéma cible
│   │   ├── nlp.py                ← [BONUS] NLP nursing notes
│   │   ├── anomaly.py            ← [BONUS] Détection d'anomalies
│   │   ├── sql_export.py         ← Export vers SQLite / SQL Server
│   │   └── agents/
│   │       ├── __init__.py
│   │       ├── base_agent.py
│   │       ├── schema_detective.py
│   │       ├── validation_agent.py
│   │       ├── clinical_reasoner.py
│   │       ├── nursing_analyst.py
│   │       ├── data_repair.py
│   │       ├── data_analyst_agent.py
│   │       ├── doc_generator.py
│   │       ├── supervisor.py
│   │       └── orchestrator.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── clinical_rules.py
│   │   ├── gender_mapping.py
│   │   └── schema_mapping.py
│   ├── data/
│   │   ├── clean/                ← Données propres (= VALIDATION)
│   │   ├── dirty/                ← Données sales (= INPUT)
│   │   ├── split/                ← Données split (4 cliniques)
│   │   └── db/                   ← SQLite database + schéma SQL
│   ├── tests/
│   │   ├── test_ingestion.py
│   │   ├── test_validator.py
│   │   └── test_mapper.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env
│
└── frontend/                     ← DOSSIER FRONTEND
    └── (voir section Frontend)
```

### Règle absolue : contracts.py

Le fichier `medmap/contracts.py` est **DÉJÀ CRÉÉ**. Il contient :
- 20 dataclasses partagés entre front et back
- 12 enums (Severity, RiskLevel, PipelineStatus, etc.)
- Les clés du session_state
- La fonction init_session_state

Le backend **IMPORTE** ces types depuis contracts.py.
Les endpoints FastAPI **RETOURNENT** ces types (convertis en JSON).
Le frontend a le miroir en `contracts.ts`.

Si un dev modifie un type, il prévient l'autre.

---

<a name="contrat"></a>

## 4. CONTRAT PARTAGÉ

### 4.1 Python (contracts.py) — déjà créé dans medmap/

12 enums : `Severity`, `RiskLevel`, `ActionTaken`, `ProblemType`, `PassportStatus`, `AgentConfidenceBadge`, `PipelineStatus`, `MobilityStatus`, `EventType`, `Shift`, `TimelineEventType`

20 dataclasses :
`IngestionResult`, `SourceQualityScore`, `AuditLogEntry`, `AgentResult`, `ColumnMapping`, `AgentStats`, `ClinicalAlert`, `NursingNLPResult`, `ConvergenceScore`, `PatientSummary`, `LabResult`, `TimelineEvent`, `DataPassport`, `WardScore`, `AskDataResult`, `CorrectionRequest`, `CorrectionResult`, `PipelineProgress`, `StreamingProgress`, `PipelineStats`, `ROIInputs`, `ROIOutputs`

### 4.2 TypeScript (contracts.ts) — à créer dans frontend/src/types/

Miroir exact de contracts.py. Les noms de champs restent en **snake_case** (pour matcher le JSON).

```typescript
// Enums
export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type RiskLevel = "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
export type ActionTaken = "QUARANTINE" | "AUTO_CORRECT" | "FLAGGED" | "ACCEPTED" | "MANUAL_CORRECT" | "ROLLBACK";
export type ProblemType = "INVALID" | "MISSING" | "OUTLIER" | "CORRECTED" | "STRUCTURAL" | "DUPLICATE";
export type PassportStatus = "QUARANTINE" | "CLEAN" | "PENDING_REVIEW";
export type AgentConfidenceBadge = "AUTO" | "CHECK" | "REVIEW";
export type PipelineStatus = "IDLE" | "RUNNING" | "COMPLETED" | "ERROR";
export type MobilityStatus = "INDEPENDENT" | "ASSISTED" | "WHEELCHAIR" | "BED_BOUND";
export type EventType = "ORDER" | "CHANGE" | "ADMIN";
export type Shift = "Early" | "Late" | "Night";
export type TimelineEventType = "LAB" | "MOTION_HOURLY" | "MOTION_1HZ" | "MEDICATION" | "NURSING" | "ASSESSMENT" | "ALERT";

// Interfaces — voir contracts.py pour la doc complète de chaque champ
export interface IngestionResult { source_file: string; rows_total: number; rows_loaded: number; encoding_detected: string; delimiter_detected: string; warnings: string[]; }
export interface SourceQualityScore { source_file: string; score: number; rows_imported: number; rows_quarantined: number; values_auto_corrected: number; errors_by_category: Record<string, number>; }
export interface AuditLogEntry { source_file: string; case_id: string; table_name: string; column_name: string; original_value: string; cleaned_value: string | null; error_type: string; severity: Severity; action_taken: ActionTaken; corrected_by: string | null; correction_timestamp: string | null; row_number: number | null; }
export interface AgentResult { agent_name: string; decision: string; confidence: number; reasoning: string; alternative: string | null; needs_human_review: boolean; metadata: Record<string, unknown>; badge: AgentConfidenceBadge; }
export interface ColumnMapping { source_file: string; source_column: string; target_column: string; confidence: number; badge: AgentConfidenceBadge; status: "CONSENSUS" | "CONFLICT" | "UNCERTAIN"; detective_result: AgentResult | null; validation_result: AgentResult | null; supervisor_decision: string | null; alternative_target: string | null; }
export interface AgentStats { total_columns: number; auto_mapped: number; conflicts: number; escalated: number; agent_progress: Record<string, { processed: number; total: number }>; }
export interface ClinicalAlert { case_id: string; rule_name: string; severity: Severity; message: string; sources_involved: string[]; triggered_values: Record<string, unknown>; timestamp_generated: string; sbar: { S: string; B: string; A: string; R: string } | null; is_treated: boolean; treated_by: string | null; treated_at: string | null; }
export interface NursingNLPResult { case_id: string; shift: Shift; report_date: string; pain_level: number | null; mobility_status: MobilityStatus | null; wound_grade: string | null; deterioration_flag: boolean; deterioration_signs: string[]; }
export interface ConvergenceScore { case_id: string; total_score: number; risk_level: RiskLevel; breakdown: { labs: number; motion: number; medication: number; nursing: number; assessment: number; }; top_contributors: string[]; computed_at: string; }
export interface PatientSummary { case_id: string; patient_id: string | null; age: number | null; gender: "M" | "F" | null; ward: string | null; admission_date: string | null; discharge_date: string | null; primary_icd10: string | null; primary_icd10_desc: string | null; convergence_score: ConvergenceScore | null; }
export interface LabResult { parameter_name: string; value: string | null; flag: "H" | "L" | "HH" | "LL" | null; ref_low: string | null; ref_high: string | null; original_value: string | null; was_corrected: boolean; }
export interface TimelineEvent { event_type: TimelineEventType; timestamp: string; data: Record<string, unknown>; source_file: string | null; alert_message: string | null; }
export interface DataPassport { passport_id: number | null; case_id: string; table_name: string; field_name: string; raw_value: string; cleaned_value: string | null; detected_by: string; problem_type: ProblemType; problem_detail: string; action_taken: ActionTaken; confidence: number; validated_by: string | null; fhir_alignment: string | null; status: PassportStatus; source_file: string | null; row_number: number | null; created_at: string | null; updated_at: string | null; }
export interface WardScore { ward_name: string; score: number; nb_patients: number; nb_errors: number; rank: number; axes: { completude: number; dates: number; valeurs_cliniques: number; ids: number; encodage: number; }; }
export interface AskDataResult { question: string; sql_generated: string; results_as_dicts: Record<string, unknown>[] | null; narrative_answer: string | null; error: string | null; row_count: number; execution_time_ms: number; }
export interface CorrectionRequest { audit_log_id: number; case_id: string; table_name: string; column_name: string; original_value: string; current_value: string | null; new_value: string | null; action: ActionTaken; corrected_by: string; }
export interface CorrectionResult { success: boolean; audit_log_id: number; previous_value: string | null; new_value: string | null; action: ActionTaken; error: string | null; }
export interface PipelineProgress { status: PipelineStatus; current_step: string; step_number: number; total_steps: number; progress_pct: number; step_detail: string | null; errors: string[]; }
export interface StreamingProgress { processed: number; total: number; pct: number; falls: number; anomalies: number; patients: number; }
export interface PipelineStats { sources_processed: number; total_rows: number; rows_imported: number; rows_quarantined: number; errors_by_category: Record<string, number>; errors_by_dataset: Record<string, number>; critical_alerts: ClinicalAlert[]; ward_scores: Record<string, WardScore>; processing_time_seconds: number; top_patient_risk: ConvergenceScore | null; }
export interface ROIInputs { nb_institutions: number; nb_cases_per_year: number; complication_rate: number; cost_per_complication: number; prevention_rate: number; }
export interface ROIOutputs { cases_total: number; complications: number; prevented: number; savings_per_year: number; time_saved_hours: number; }
```

---

<a name="pipeline"></a>

## 5. BACKEND — PIPELINE

═══════════════════════════════════════════════════════════

### MODULE 1 : INGESTION (pipeline/ingestion.py)

Créer une classe `DataIngester` avec les fonctionnalités suivantes :

#### 1.1 AUTO-DÉTECTION DU DÉLIMITEUR
- Tester virgule et point-virgule
- Utiliser csv.Sniffer en fallback
- Cas spécial : epaAC-Data-3 a le header en semicolons et les données en virgules → détecter le mismatch et corriger automatiquement

#### 1.2 AUTO-DÉTECTION DE L'ENCODAGE
- Utiliser chardet pour détecter UTF-8 vs Latin-1
- Fallback : essayer UTF-8, puis latin-1, puis cp1252
- Logger l'encodage détecté dans le rapport qualité

#### 1.3 LECTURE DES SOURCES — 3 groupes

Implémenter une méthode `load(filepath)` qui retourne un DataFrame et détecte automatiquement le type de fichier par son **contenu (colonnes), pas par son nom**.

**Groupe A — Sources de base (dirty + clean) — 8 fichiers principaux :**

Noms différents entre clean et dirty — détecter par colonnes.

**a) synth_labs_1000_cases.csv et .xlsx**
- CSV standard ou XLSX
- ~1000 lignes, 64 colonnes
- Identifiants : case_id (CASE-0001...), patient_id (6 chiffres)

**b) synthetic_cases_icd10_ops.csv**
- 50 cas, colonnes multi-valeurs séparées par virgules (secondary_icd10_codes, ops_codes) → parser en listes

**c) synthetic_device_motion_fall_data.csv**
- ~24,000 lignes, données horaires
- Colonnes binaires (0/1) pour bed_exit_detected et fall_event

**d) synthetic_device_raw_1hz_motion_fall.csv (9.99 MB)**
- OBLIGATOIRE : lire en chunks de 5000 lignes (`pd.read_csv` avec `chunksize=5000`)
- Afficher une barre de progression pendant le chargement
- Ne jamais charger ce fichier entier en mémoire d'un coup

**e) synthetic_medication_raw_inpatient.csv (~14,553 lignes)**
- 3 types d'événements : ORDER, CHANGE, ADMIN
- Conserver le type d'événement comme colonne

**f) synthetic_nursing_daily_reports_en.csv**
- 182 notes texte libre, 50 cas, 3 shifts (Early/Late/Night)
- [BONUS] Passer au module NLP après ingestion

**g) epaAC-Data-1 à epaAC-Data-5**
- Format semicolon-délimité
- 900+ colonnes, noms de colonnes en allemand
- Encodage potentiellement Latin-1
- Champs obligatoires par entrée : type d'assessment, date, case_id → exclure silencieusement les lignes sans ces 3 champs

**h) IID-SID-ITEM.csv** ⚠️
- Table de correspondance officielle pour mapper les colonnes epaAC
- Parser avec `on_bad_lines='skip'` (erreur quoting ligne 4481)
- Format : IID (item ID) | SID (section ID) | colonne cible SQL

**Groupe B — Dossier split : 4 cliniques × 7 types = 28 fichiers :**

Parcourir automatiquement `split_data_pat_case_altered/`. Cas spéciaux :
- `clinic_4_epaAC-Data.xlsx` → lire avec openpyxl
- `clinic_4_nursing.pdf` → lire avec pdfplumber (extraire tables ou texte libre)

```python
# Lecture PDF avec pdfplumber
import pdfplumber

def load_pdf_nursing(filepath):
    rows = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    rows.extend(table)
            else:
                text = page.extract_text()
                rows.append({"raw_text": text, "source": filepath})
    return pd.DataFrame(rows)
```

**Groupe C — Fichier de référence :**
- `IID-SID-ITEM.csv` → dictionnaire SAP, parser avec `on_bad_lines='skip'`

#### 1.4 RÉSULTAT DE L'INGESTION
Pour chaque fichier chargé, retourner un `IngestionResult` (contracts.py) :
```python
{
  "source_file": filename,
  "rows_total": int,
  "rows_loaded": int,
  "encoding_detected": str,
  "delimiter_detected": str,
  "warnings": [str]
}
```

═══════════════════════════════════════════════════════════

### MODULE 2 : VALIDATION ET NETTOYAGE (pipeline/validator.py + pipeline/cleaner.py)

Pour **CHAQUE** valeur traitée, logger dans un `AuditLogEntry` :
```python
{
  source_file, case_id, column, original_value,
  cleaned_value, error_type, severity, action_taken
}
```
Sévérités possibles : CRITICAL / HIGH / MEDIUM / LOW

#### 2A. VALEURS MANQUANTES
Détecter et normaliser toutes ces représentations → None/NaN :
- NULL, NaN, blank, ""
- "N/A", "n/a", "NA" (case-insensitive)
- "missing", "unknown", "keine" (case-insensitive)
- Cellules contenant uniquement des espaces ou tabs

Action : flaguer avec severity selon criticité du champ

#### 2B. NORMALISATION DES DATES
Parser multi-pass dans cet ordre :
- Pass 1 : ISO format YYYY-MM-DD
- Pass 2 : Format allemand DD.MM.YYYY
- Pass 3 : Format US MM/DD/YYYY
- Pass 4 : Mois textuels ("15. März 2025", "January 3, 2024")
- Pass 5 : Validation de range → rejeter dates < 2000 ou > 2030

Dates impossibles → flag INVALID_DATE :
- 99.99.9999
- 32.01.2024 (jour impossible)
- 00/00/0000
- 15-13-2024 (mois 13)
- 2024/00/12 (mois 0)

Résultat : date ISO normalisée ou None + flag dans l'audit log

#### 2C. VALIDATION CLINIQUE
Ranges exacts (valeurs en dehors = quarantaine) :

| Paramètre               | Range valide   | Flag si          |
|-------------------------|----------------|------------------|
| sodium_mmol_L           | 100 – 165      | <100 ou >165     |
| potassium_mmol_L        | 2.0 – 7.5      | <2.0 ou >7.5     |
| creatinine_mg_dL        | 0.3 – 15.0     | <0 ou >15        |
| egfr_mL_min_1_73m2      | 1 – 120        | <0 (impossible)  |
| glucose_mg_dL           | 20 – 600       | <20 ou >600      |
| hemoglobin_g_dL         | 3 – 25         | <0               |
| wbc_10e9_L              | 0.1 – 100      | >200             |
| platelets_10e9_L        | 10 – 1000      | <0 ou >1500      |
| crp_mg_L                | 0 – 500        | <0               |
| alt_U_L                 | 1 – 5000       | <0               |
| ast_U_L                 | 1 – 5000       | <0               |
| bilirubin_mg_dL         | 0 – 30         | <0               |
| albumin_g_dL            | 1 – 6          | <0 ou >10        |
| inr                     | 0.5 – 10       | <0 ou >15        |
| lactate_mmol_L          | 0.3 – 20       | <0               |
| bmi                     | 10 – 70        | >100 ou <5       |
| impact_magnitude_g      | 0 – 50         | <0               |

Pour chaque valeur hors range :
- Stocker valeur originale dans colonne `_raw`
- Mettre NULL dans la colonne principale
- Logger severity=CRITICAL dans l'audit log

Nettoyer les contaminations non-numériques dans les champs numériques :
- Retirer : ü, ä, ß, ^, @, $, %, # et autres caractères spéciaux
- Tenter une conversion float après nettoyage
- Si échec → NULL + log

#### 2D. NORMALISATION DU GENRE
```
"M"        → "M"
"male"     → "M"
"männlich" → "M"
"mä"       → "M"  (tronqué)
"m"        → "M"
"F"        → "F"
"female"   → "F"
"weiblich" → "F"
"f"        → "F"
"N/A"      → None
""         → None
Tout autre valeur → None + log severity=MEDIUM
```

#### 2E. NETTOYAGE DES IDs + GESTION PID DUPLIQUÉS

Pour case_id et patient_id :
- Striper espaces, tabs (\t), retours à la ligne
- Supprimer caractères spéciaux trailing/leading
- Valider format attendu :
  - case_id → regex `r'^CASE-\d{3,4}$'`
  - patient_id → regex `r'^PAT-\d{4,6}$'` ou 6 chiffres
- Si ID invalide après nettoyage → log severity=HIGH

**Gestion des PID dupliqués entre sources (clarification Discord) :**
- Détecter quand le même patient_id pointe vers des données contradictoires (ex: même PID = homme dans labs, femme dans motion data)
- Stratégie : ajouter **préfixe source** pour unicité :
  - Labs : `LAB_{patient_id}`
  - Motion data : `MOT_{patient_id}`
  - epaAC : `EPA_{patient_id}`
  - Medication : `MED_{patient_id}`
  - Nursing : `NUR_{patient_id}`
- Logger chaque PID conflictuel dans tbAuditLog avec error_type="PID_CONFLICT"

**Mapping patient_id + datetime → case_id :**
- Quand un fichier n'a pas de case_id direct
- Utiliser **patient_id + datetime** pour mapper vers le bon cas dans tbCaseData

#### 2F. DOUBLONS
- Détecter lignes 100% identiques → supprimer, garder la première
- Détecter doublons partiels sur (case_id + timestamp) pour les tables de motion data
- Logger chaque doublon supprimé avec les numéros de lignes originaux

#### 2G. CORRECTION DU DELIMITER MISMATCH (epaAC-Data-3)
Si le nombre de colonnes des lignes de données ≠ nombre de colonnes du header :
- Essayer de re-parser avec l'autre délimiteur (virgule vs semicolon)
- Si ça résout le mismatch → continuer silencieusement avec un warning
- Logger le fichier comme "structural_error_corrected"

#### 2H. FLAGS DE LABO
Normaliser les colonnes de flag (H, L, HH, LL) :
- Nettoyer les caractères spéciaux intégrés
- Valeurs valides uniquement : H, L, HH, LL, "" (normal)
- Tout autre valeur → None + log

═══════════════════════════════════════════════════════════

### MODULE 3 : MAPPING (pipeline/mapper.py)

Mapper chaque source nettoyée vers les 7 tables cibles. Les mappings sont **FIXES et hardcodés** (pas de LLM requis pour la version de base).

**Pour epaAC-Data :** utiliser IID-SID-ITEM.csv comme table de référence officielle.

#### TABLE tbCaseData
Source principale : synth_labs + epaAC-Data
```
case_id          → coPatientId (après nettoyage)
patient_id       → coPatientId (avec préfixe source si conflit)
sex (normalisé)  → coGender
age_years        → coAgeYears
primary_icd10    → coIcd (depuis icd10_ops)
```

#### TABLE tbImportLabsData
Source : synth_labs_1000_cases
```
coCaseId         ← case_id (FK vers tbCaseData)
Pour chaque paramètre de labo (15 paramètres) :
  [param]_value   → co[Param]Value    (nvarchar — stocker comme string)
  [param]_flag    → co[Param]Flag     (normalisé H/L/HH/LL)
  [param]_ref_low → co[Param]RefLow
  [param]_ref_high→ co[Param]RefHigh
```
IMPORTANT : toutes ces colonnes sont nvarchar dans la DB → stocker comme string, PAS comme float → stocker aussi la valeur originale dans colonne `_raw` pour l'audit

#### TABLE tbImportIcd10Data
Source : synthetic_cases_icd10_ops
```
coCaseId                  ← case_id
coAdmission_date          ← admission_date (normalisé ISO)
coDischarged_date         ← discharge_date (normalisé ISO)
coPrimary_icd10_code      ← primary_icd10_code
coPrimary_icd10_desc      ← primary_icd10_description
coSecondary_icd10_codes   ← secondary_icd10_codes (string)
coOps_codes               ← ops_codes (string)
coWard                    ← ward
```

#### TABLE tbImportDeviceMotionData
Source : synthetic_device_motion_fall_data
```
coCaseId                       ← patient_id (FK)
coTimestamp                    ← timestamp
coMovement_index_0_100         ← movement_index_0_100
coMicro_movements_count        ← micro_movements_count
coBed_exit_detected            ← bed_exit_detected_0_1
coFall_event                   ← fall_event_0_1
coImpact_magnitude_g           ← impact_magnitude_g
coPost_fall_immobility_minutes ← post_fall_immobility_minutes
```

#### TABLE tbImportDevice1HzMotionData
Source : synthetic_device_raw_1hz_motion_fall (chunks)
```
coCaseId          ← patient_id
coTimestamp       ← timestamp
coAccel_x         ← accel_x
coAccel_y         ← accel_y
coAccel_z         ← accel_z
coAccel_magnitude ← accel_magnitude
coPressure_zone_1 ← pressure_zone_1
coPressure_zone_2 ← pressure_zone_2
coPressure_zone_3 ← pressure_zone_3
coPressure_zone_4 ← pressure_zone_4
coMovement_score  ← movement_score
coFall_event      ← fall_event_0_1
```

#### TABLE tbImportMedicationInpatientData
Source : synthetic_medication_raw_inpatient
```
coCaseId                  ← case_id
coEvent_type              ← event_type (ORDER/CHANGE/ADMIN)
coMedication_code_atc     ← medication_code_atc
coMedication_name         ← medication_name
coRoute                   ← route
coDose                    ← dose
coFrequency               ← frequency
coPrescriber_role         ← prescriber_role
coAdministration_status   ← administration_status
coEvent_datetime          ← event_datetime (normalisé ISO)
```

#### TABLE tbImportNursingDailyReportsData
Source : synthetic_nursing_daily_reports
```
coCaseId                  ← case_id
coReport_date             ← report_date (normalisé ISO)
coShift                   ← shift (Early/Late/Night)
coNursing_note_free_text  ← note_text (tronqué à 256 chars)
coPain_level_extracted    ← [BONUS] résultat NLP
coMobility_extracted      ← [BONUS] résultat NLP
coWound_grade_extracted   ← [BONUS] résultat NLP
```

#### TABLE tbImportAcData
Sources : epaAC-Data-1 à 5 (clean) + epaAC-Data-3 (dirty) + clinic_X_epaAC (split)

**⚠️ DEUX FORMATS COMPLÈTEMENT DIFFÉRENTS à gérer :**

**Format A — Clean (codes SAP)** : colonnes comme `EPA0001`, `PATGEB`, `MANDT`, `EPAST0BTS`
→ Utiliser **IID-SID-ITEM.csv** pour décoder :
```python
iid_map = pd.read_csv("IID-SID-ITEM.csv", sep=";",
                       on_bad_lines='skip', encoding='latin-1')
decoder = dict(zip(iid_map['ItmIID'], iid_map['ItmName255_EN']))
df_epac.rename(columns=decoder, inplace=True)
```

**Format B — Dirty/Split (noms allemands)** : colonnes comme `Körpergröße`, `BMI`, `AufnDat`
→ Mapping hardcodé :
```
FallID / PATFAL    → coCaseId
PID / PATFOE       → coPatientId (avec préfixe EPA_ si conflit)
AufnDat / PATADT   → coAdmissionDate (normaliser date)
Alter              → coAgeYears
Körpergröße / Koerpergroesse → coHeight
Körpergewicht / Koerpergewicht → coWeight
BMI                → coBmi (valider range)
```

**Détecter le format automatiquement :**
```python
def detect_epac_format(df):
    if any(col.startswith('EPA') for col in df.columns):
        return 'SAP_CODES'
    elif 'AufnDat' in df.columns or 'Körpergröße' in df.columns:
        return 'GERMAN_TEXT'
    return 'UNKNOWN'
```

Colonnes cibles communes :
```
coMaxDekuGrad        ← champ Dekubitus max grade
coDekubitusWertTotal ← score total Dekubitus
coLastAssessment     ← date dernier assessment
```

═══════════════════════════════════════════════════════════

### MODULE 4 : NLP — ⭐ BONUS OPTIONNEL (pipeline/nlp.py)

> Les organisateurs ont confirmé que l'analyse patient n'est PAS obligatoire.

spaCy avec modèle `en_core_web_sm` (offline). Extraire de chaque note nursing :

1. **NIVEAU DE DOULEUR** — Patterns : "pain level X/10", "pain score X", "VAS X" → int 0-10
2. **MOBILITÉ** — Patterns : "mobilised", "ambulating", "bed-bound", "wheelchair" → INDEPENDENT / ASSISTED / WHEELCHAIR / BED_BOUND
3. **GRADE DE PLAIE** — Patterns : "wound grade X", "stage X pressure", "healing well" → grade 1-4 ou "HEALING"
4. **SIGNES DE DÉTÉRIORATION** — Patterns : "confused", "deteriorating", "refused medication", "agitated" → boolean + liste signes

Retourner `NursingNLPResult` (contracts.py) par note.

═══════════════════════════════════════════════════════════

### MODULE 5 : DÉTECTION D'ANOMALIES — ⭐ BONUS OPTIONNEL (pipeline/anomaly.py)

> Bonus uniquement. Ne pas implémenter avant le pipeline de base.

6 règles de corrélation cross-dataset par case_id :

| # | Règle | Conditions | Sévérité |
|---|-------|-----------|----------|
| 1 | AKI probable | creatinine > 3.0 ET egfr < 20 ET potassium > 5.5 | CRITICAL |
| 2 | Sepsis possible | crp > 100 ET lactate > 2.0 ET wbc > 12 | CRITICAL |
| 3 | Risque chute élevé | fall_event=1 ET post_fall_immobility > 15min | HIGH |
| 4 | Médicament dangereux + AKI | egfr < 30 ET medication contient Metformin/NSAR/Aminoglycoside | CRITICAL |
| 5 | Détérioration multi-source | deterioration_flag=True ET (REFUSED OU fall_event=1) | HIGH |
| 6 | Anticoagulant + INR | Warfarin/Phenprocoumon ET (inr < 2.0 ou inr > 4.0) | HIGH |

Retourner `ClinicalAlert` (contracts.py) par alerte.

═══════════════════════════════════════════════════════════

### MODULE 6 : EXPORT SQL (pipeline/sql_export.py)

#### SQLite (défaut, pour la démo offline)
- Créer la DB depuis le schéma `CreateImportTables.sql`
- Adapter la syntaxe T-SQL → SQLite (IDENTITY → AUTOINCREMENT, NVARCHAR → TEXT)
- Insérer dans cet ordre (respecter les FK) :
  1. tbCaseData
  2. tbImportLabsData
  3. tbImportIcd10Data
  4. tbImportAcData
  5. tbImportDeviceMotionData
  6. tbImportDevice1HzMotionData (chunks)
  7. tbImportMedicationInpatientData
  8. tbImportNursingDailyReportsData

#### SQL Server (optionnel, activé via config)
- Connexion via SQLAlchemy + pyodbc
- Connection string dans .env : `MSSQL_CONNECTION_STRING`
- BULK INSERT pour le fichier 1Hz

#### DUAL VALUE STORAGE + tbAuditLog
```sql
tbAuditLog (
  source_file, case_id, table_name,
  column_name, original_value, cleaned_value,
  error_type, severity, action_taken,
  corrected_by,        -- NULL=auto, sinon user_id
  correction_timestamp
)
```

#### tbDataPassport (BONUS Feature 6)
```sql
CREATE TABLE tbDataPassport (
  passport_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id       TEXT,
  table_name    TEXT,
  field_name    TEXT,
  raw_value     TEXT,
  cleaned_value TEXT,
  detected_by   TEXT,
  problem_type  TEXT,  -- INVALID / MISSING / OUTLIER / CORRECTED
  problem_detail TEXT,
  action_taken  TEXT,  -- QUARANTINE / AUTO_CORRECT / FLAGGED
  confidence    REAL,
  validated_by  TEXT,
  fhir_alignment TEXT,
  status        TEXT,  -- QUARANTINE / CLEAN / PENDING_REVIEW
  created_at    TEXT,
  updated_at    TEXT
)
```

═══════════════════════════════════════════════════════════

### MODULE 7 : AGENTS — ⭐ BONUS (pipeline/agents/)

#### base_agent.py
Classe abstraite `AgentBase` :
- attributs : name, confidence_threshold (défaut 0.75)
- méthode abstraite : `reason(input: dict) -> AgentResult`
- méthode `log_decision(decision, confidence, reasoning) -> dict`

#### schema_detective.py
Analyse une colonne inconnue et propose un mapping avec score de confiance.
```python
KNOWN_PATTERNS = {
    "weight|gewicht|poids|koerpergewicht": ("coWeight", 0.95),
    "height|groesse|taille|koerpergroesse": ("coHeight", 0.95),
    "egfr|glomerular|filtration": ("coEgfr_value", 0.97),
    "creatinine|kreatinin": ("coCreatinine_value", 0.97),
    "sodium|natrium": ("coSodium_value", 0.96),
    "bmi|body_mass": ("coBmi", 0.98),
    "gender|sex|geschlecht": ("coGender", 0.99),
    "case_id|fallid|caseid": ("coCaseId", 0.99),
    "patient_id|pid|patientid": ("coPatientId", 0.99),
}
```
Badges : confidence >= 0.90 → 🟢 AUTO | 0.70-0.89 → 🟡 CHECK | < 0.70 → 🔴 REVIEW

#### validation_agent.py
Challenge les décisions du detective. Vérifie cohérence valeurs/type, cohérence croisée (BMI = poids/taille²).

#### supervisor.py
Reçoit les résultats Schema Detective + Validation Agent. Tranche :
- CONSENSUS (accord + confiance > 0.85) → mapping auto
- CONFLIT → escalade humain + affichage deux options
- INCERTAIN → escalade auto

Stats : total_columns, auto_mapped, conflicts, escalated

#### clinical_reasoner.py
- **Convergence Score** (0-100) : Labs max 35 + Motion max 25 + Meds max 20 + Nursing max 15 + Assessment max 5
- **SBAR generator** : appel Claude API → fiche S/B/A/R. Fallback offline : template.
- **Anomaly Explainer** : explication physiologique pour valeurs anormales. Fallback offline : hardcodé.

#### nursing_analyst.py
Analyse NLP des notes infirmières (délègue à nlp.py).

#### data_repair.py
Propose des réparations automatiques pour les valeurs quarantinées.

#### data_analyst_agent.py (Ask Your Data)
Question → prompt Claude (claude-sonnet-4-6) → SQL → exécution → narrative.
Fallback sans API key : affiche juste le SQL.

#### doc_generator.py (Auto-Documentation)
Appel Claude API → rapport professionnel (résumé, fichier problématique, patients critiques, taux de récupération, recommandations).
Fallback : template Python avec stats insérées.

#### orchestrator.py
Coordonne tous les agents. `run_pipeline()` → yield `PipelineProgress` pour le streaming.

═══════════════════════════════════════════════════════════

### MODULE 8 : CONFIGURATION (config/)

```python
# config/settings.py
DB_TYPE = "sqlite"
DB_PATH = "data/db/medmap.db"
MSSQL_CONNECTION_STRING = os.getenv("MSSQL_CONNECTION_STRING")
CHUNK_SIZE = 5000
LOG_LEVEL = "INFO"
NLP_MODEL = "en_core_web_sm"
PID_PREFIX_STRATEGY = True
```

```python
# config/clinical_rules.py
CLINICAL_RANGES = {
    "sodium_mmol_L": (100, 165),
    "potassium_mmol_L": (2.0, 7.5),
    "creatinine_mg_dL": (0.3, 15.0),
    "egfr_mL_min_1_73m2": (1, 120),
    "glucose_mg_dL": (20, 600),
    "hemoglobin_g_dL": (3, 25),
    "wbc_10e9_L": (0.1, 100),
    "platelets_10e9_L": (10, 1000),
    "crp_mg_L": (0, 500),
    "alt_U_L": (1, 5000),
    "ast_U_L": (1, 5000),
    "bilirubin_mg_dL": (0, 30),
    "albumin_g_dL": (1, 6),
    "inr": (0.5, 10),
    "lactate_mmol_L": (0.3, 20),
    "bmi": (10, 70),
    "impact_magnitude_g": (0, 50),
}
```

```python
# config/gender_mapping.py
GENDER_MAP = {
    "M": "M", "male": "M", "männlich": "M", "mä": "M", "m": "M",
    "F": "F", "female": "F", "weiblich": "F", "f": "F",
    "N/A": None, "": None
}
```

---

<a name="api"></a>

## 6. BACKEND — API FASTAPI (25 endpoints)

### api/main.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import (
    pipeline, upload, overview, agents,
    patients, alerts, quality, ask, corrections,
)

app = FastAPI(title="MEDMAP API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(overview.router, prefix="/api/overview", tags=["overview"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(patients.router, prefix="/api/patients", tags=["patients"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(quality.router, prefix="/api/quality", tags=["quality"])
app.include_router(ask.router, prefix="/api/ask", tags=["ask"])
app.include_router(corrections.router, prefix="/api/corrections", tags=["corrections"])
```

### api/dependencies.py

```python
import sqlite3
from config.settings import DB_PATH

_conn = None

def get_db():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn
```

### Tous les endpoints

**PIPELINE** (api/routers/pipeline.py) :
```
POST /api/pipeline/start         Body: { "data_folder": "clean" | "dirty" }
                                 → Lance le pipeline en background (threading)
                                 → Retourne PipelineProgress initial
GET  /api/pipeline/progress      → PipelineProgress actuel
GET  /api/pipeline/stats         → PipelineStats (après complétion)
GET  /api/pipeline/streaming-progress → StreamingProgress (pendant 1Hz)
```

**UPLOAD** (api/routers/upload.py) :
```
POST /api/upload                 → Multipart file upload → IngestionResult[]
```

**OVERVIEW** (api/routers/overview.py) :
```
GET  /api/overview/quality-scores → SourceQualityScore[]
GET  /api/overview/ward-scores    → WardScore[]
POST /api/overview/generate-report → { "report": string }
```

**AGENTS** (api/routers/agents.py) :
```
GET  /api/agents/stats            → AgentStats
GET  /api/agents/mappings         Query: ?badge=AUTO,CHECK&source=labs&status=CONSENSUS
                                  → ColumnMapping[]
GET  /api/agents/decisions        Query: ?limit=20
                                  → ColumnMapping[]
```

**PATIENTS** (api/routers/patients.py) :
```
GET  /api/patients                Query: ?ward=Geriatrie&limit=50 → PatientSummary[]
GET  /api/patients/{case_id}      → PatientSummary
GET  /api/patients/{case_id}/labs → LabResult[]
GET  /api/patients/{case_id}/timeline → TimelineEvent[] (fusionner toutes sources, trier par timestamp, injecter alertes)
GET  /api/patients/{case_id}/medications → TimelineEvent[] filtré
GET  /api/patients/{case_id}/nursing → NursingNLPResult[]
GET  /api/patients/{case_id}/convergence → ConvergenceScore
GET  /api/patients/{case_id}/passports → DataPassport[]
```

**ALERTS** (api/routers/alerts.py) :
```
GET   /api/alerts                 Query: ?severity=CRITICAL,HIGH&treated=false
                                  → ClinicalAlert[]
PATCH /api/alerts/{case_id}/{rule_name}  Body: { "treated_by": string }
                                         → ClinicalAlert (updated)
```

**QUALITY** (api/routers/quality.py) :
```
GET  /api/quality/audit-log       Query: ?source=labs&severity=CRITICAL&limit=100
                                  → AuditLogEntry[]
GET  /api/quality/passports       Query: ?status=QUARANTINE&problem_type=INVALID
                                  → DataPassport[]
GET  /api/quality/completeness    → Record<string, Record<string, number>>
                                  Matrice source × colonne avec % complétude
```

**ASK YOUR DATA** (api/routers/ask.py) :
```
POST /api/ask                     Body: { "question": string }
                                  → AskDataResult (SQL + résultats + narrative)
GET  /api/ask/history             → AskDataResult[]
```

**CORRECTIONS** (api/routers/corrections.py) :
```
GET  /api/corrections/pending     → DataPassport[] WHERE status=PENDING_REVIEW
POST /api/corrections/apply       Body: CorrectionRequest → CorrectionResult
POST /api/corrections/rollback    Body: { "audit_log_id": int } → CorrectionResult
GET  /api/corrections/history     → CorrectionResult[]
```

**TOTAL : 25 endpoints.**

---

<a name="frontend"></a>

## 7. FRONTEND — SPEC COMPLÈTE (9 pages)

### Point de départ : le starter next-shadcn-dashboard-starter

Le projet part du starter existant qui contient DÉJÀ :
- Layout : sidebar collapsible + header + PageContainer + scroll area
- Thèmes : 6 thèmes dont "Claude", dark/light mode
- Composants shadcn/ui complets
- Recharts pour les graphiques
- TanStack Table pour les tableaux
- React Hook Form + Zod
- KBar (Cmd+K)
- Composants healthcare existants : AlertsPanel, AnomalyDetectionTable, DataQualityPanel, DataSourcesView, ManualCorrectionTable

**À SUPPRIMER** : Clerk (auth), Sentry, pages Product/Kanban/Billing/Workspaces/Teams/Exclusive, RBAC, OrgSwitcher.

**À GARDER** : Layout, composants shadcn/ui, thèmes, Recharts, composants healthcare (à adapter), KBar.

### Structure frontend/

```
frontend/
├── .env.local                    # API_URL + USE_MOCKS=true
├── src/
│   ├── app/dashboard/
│   │   ├── overview/page.tsx     # Page 1
│   │   ├── agents/page.tsx       # Page 2
│   │   ├── time-travel/page.tsx  # Page 3
│   │   ├── quality/page.tsx      # Page 4
│   │   ├── patient/page.tsx      # Page 5
│   │   ├── alerts/page.tsx       # Page 6
│   │   ├── ask/page.tsx          # Page 7
│   │   ├── corrections/page.tsx  # Page 8
│   │   └── roi/page.tsx          # Page 9
│   ├── types/contracts.ts        # Miroir de contracts.py
│   ├── lib/
│   │   ├── api.ts                # Fetch wrapper + mock switch
│   │   ├── mock-data.ts          # Données factices complètes
│   │   └── constants.ts          # Couleurs, icônes, styles
│   ├── hooks/
│   │   ├── use-api.ts            # Hook data fetching
│   │   └── use-pipeline.ts       # Polling pipeline progress
│   └── features/
│       ├── overview/components/  # pipeline-control, source-quality-grid, ward-scoreboard, etc.
│       ├── agents/components/    # agent-progress-list, confidence-glass, supervisor-log
│       ├── time-travel/components/ # patient-timeline, timeline-event-card
│       ├── quality/components/   # error-table, completeness-heatmap, before-after-view
│       ├── patient/components/   # clinical-summary, lab-results-table, nursing-notes, data-passport-modal
│       ├── alerts/components/    # sbar-alert-card, sbar-display, alert-filters
│       ├── ask/components/       # chat-interface, suggestion-chips, query-result
│       ├── corrections/components/ # correction-queue, correction-form, correction-history
│       └── roi/components/       # roi-calculator
```

### Fetch wrapper (src/lib/api.ts)

```typescript
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === 'true';

export async function api<T>(method: 'GET' | 'POST' | 'PATCH', path: string, body?: unknown): Promise<T> {
  if (USE_MOCKS) {
    // Retourne données factices depuis mock-data.ts
    // Delay simulé 200-500ms
  }
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json();
}
```

### Les 9 pages

**PAGE 1 — Overview** : Stats globales, pipeline control, source quality grid (cartes par fichier avec score), ward scoreboard (médailles + radar), streaming visualizer (1Hz), report generator.

**PAGE 2 — Agent Orchestra** : 4 métriques agents, 6 barres de progression (un par agent), Confidence Glass (tableau filtrable 🟢🟡🔴), dernières décisions Supervisor.

**PAGE 3 — Data Time Travel** : Select patient, timeline verticale croisant toutes les sources (LAB=bleu, MÉDOC=vert, CAPTEUR=orange, NURSING=violet, ALERTE=rouge). Alertes auto injectées. Tooltip au hover.

**PAGE 4 — Data Quality** : 4 tabs — Erreurs (tableau filtrable), Catégories (barres Recharts), Complétude (heatmap source×colonne), Before/After (rouge/vert, cliquable → Data Passport).

**PAGE 5 — Vue Patient** : Select patient, résumé démographique + convergence score (badge coloré 0-100), 5 tabs (Labo coloré H/L/HH/LL, Mouvement/chutes, Médocs + alertes, Nursing NLP, Data Lineage avec icône 🛂).

**PAGE 6 — Alertes SBAR** : Filtres sévérité/case/règle. Cartes avec S/B/A/R formaté (ou message seul si offline). Boutons Voir patient / Marquer traité / Export.

**PAGE 7 — Ask Your Data** : Chat avec suggestions cliquables, SQL collapsible, résultats en tableau, narrative. Historique.

**PAGE 8 — Corrections** : 2 tabs — En attente (queue avec Accepter/Corriger/Quarantaine), Historique (tableau + bouton Rollback avec AlertDialog).

**PAGE 9 — ROI Calculator** : 5 Sliders (nb_institutions, cas/an, taux complications, coût, taux prévention). Calculs en temps réel (useMemo). 4 Cards résultats. **100% frontend, aucun appel API.**

### Navigation sidebar

```typescript
// src/config/nav-config.ts
export const navItems: NavItem[] = [
  { title: 'Overview',        url: '/dashboard/overview',     icon: 'dashboard' },
  { title: 'Agent Orchestra', url: '/dashboard/agents',       icon: 'aiAgent' },
  { title: 'Time Travel',     url: '/dashboard/time-travel',  icon: 'clock' },
  { title: 'Data Quality',    url: '/dashboard/quality',      icon: 'chart' },
  { title: 'Patient View',    url: '/dashboard/patient',      icon: 'patient' },
  { title: 'SBAR Alerts',     url: '/dashboard/alerts',       icon: 'warning' },
  { title: 'Ask Your Data',   url: '/dashboard/ask',          icon: 'chat' },
  { title: 'Corrections',     url: '/dashboard/corrections',  icon: 'userPen' },
  { title: 'ROI Calculator',  url: '/dashboard/roi',          icon: 'billing' },
];
```

### Constantes de design

```typescript
// src/lib/constants.ts
export const SEVERITY_STYLES = {
  CRITICAL: { badge: 'destructive', bg: 'bg-red-500/10', text: 'text-red-500', dot: '🔴' },
  HIGH:     { badge: 'outline', bg: 'bg-orange-500/10', text: 'text-orange-500', dot: '🟠' },
  MEDIUM:   { badge: 'outline', bg: 'bg-yellow-500/10', text: 'text-yellow-500', dot: '🟡' },
  LOW:      { badge: 'secondary', bg: 'bg-green-500/10', text: 'text-green-500', dot: '🟢' },
};

export const TIMELINE_STYLES = {
  LAB:           { icon: '📊', color: 'border-l-blue-500',   label: 'Labo' },
  MEDICATION:    { icon: '💊', color: 'border-l-green-500',  label: 'Médicament' },
  MOTION_HOURLY: { icon: '📡', color: 'border-l-orange-500', label: 'Capteur' },
  NURSING:       { icon: '📝', color: 'border-l-purple-500', label: 'Nursing' },
  ASSESSMENT:    { icon: '📋', color: 'border-l-gray-500',   label: 'Assessment' },
  ALERT:         { icon: '⚠️', color: 'border-l-red-500',    label: 'Alerte' },
};

export const SUGGESTED_QUESTIONS = [
  "Combien de patients ont chuté avec un eGFR < 30 ?",
  "Quel service a le plus d'erreurs de données ?",
  "Quels patients ont un score de risque critique ?",
  "Patients sous anticoagulants avec INR anormal ?",
  "Quels médicaments ont été le plus souvent refusés ?",
];
```

### Comment merger frontend et backend

1. Le backend lance : `cd medmap && uvicorn api.main:app --port 8000`
2. Le frontend change : `NEXT_PUBLIC_USE_MOCKS=false`
3. `npm run dev` → tout marche
4. `git merge` → zéro conflit (dossiers séparés)

---

<a name="bonus"></a>

## 8. FEATURES BONUS — RÉCAPITULATIF (1-11)

| # | Feature | Backend | Frontend | API |
|---|---------|---------|----------|-----|
| 1 | Multi-Agent + Confidence Glass | pipeline/agents/ (7 agents) | agents/page.tsx | /api/agents/* |
| 2 | Data Time Travel | endpoint /timeline | time-travel/page.tsx | /api/patients/{id}/timeline |
| 3 | Patient Convergence Score | clinical_reasoner.py | clinical-summary.tsx | /api/patients/{id}/convergence |
| 4 | Ask Your Data | data_analyst_agent.py | ask/page.tsx | /api/ask |
| 5 | SBAR + Anomaly Explainer | clinical_reasoner.py | sbar-alert-card.tsx | /api/alerts |
| 6 | Data Passport | tbDataPassport + sql_export | data-passport-modal.tsx | /api/quality/passports |
| 7 | Ward Quality Scoreboard | overview.py calcul | ward-scoreboard.tsx | /api/overview/ward-scores |
| 8 | ROI Calculator | **aucun** (100% front) | roi-calculator.tsx | aucun |
| 9 | Auto-Documentation | doc_generator.py | report-generator.tsx | /api/overview/generate-report |
| 10 | Before/After Repair View | qualité/passports | before-after-view.tsx | /api/quality/passports |
| 11 | Live 1Hz Streaming | ingestion.py chunks | streaming-visualizer.tsx | /api/pipeline/streaming-progress |

---

<a name="infra"></a>

## 9. REQUIREMENTS, DOCKER, VARIABLES D'ENV

### requirements.txt (backend)

```
fastapi>=0.110.0
uvicorn>=0.27.0
python-multipart>=0.0.7
pandas>=2.0.0
numpy>=1.24.0
openpyxl>=3.1.0
chardet>=5.0.0
python-dateutil>=2.8.0
sqlalchemy>=2.0.0
pdfplumber>=0.10.0
plotly>=5.18.0
pyodbc>=5.0.0
python-dotenv>=1.0.0
pydantic>=2.0.0
spacy>=3.7.0
anthropic>=0.25.0
```

### Dockerfile backend

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN python -m spacy download en_core_web_sm
COPY . .
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Dockerfile frontend

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

### docker-compose.yml (racine start_hack/)

```yaml
version: '3.8'
services:
  backend:
    build: ./medmap
    ports:
      - "8000:8000"
    volumes:
      - ./medmap/data:/app/data
    env_file:
      - ./medmap/.env

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
      - NEXT_PUBLIC_USE_MOCKS=false
    depends_on:
      - backend
```

### Variables d'environnement (.env)

```
ANTHROPIC_API_KEY=your_key_here
DB_TYPE=sqlite
DB_PATH=data/db/medmap.db
MSSQL_CONNECTION_STRING=
CHUNK_SIZE=5000
NLP_MODEL=en_core_web_sm
LOG_LEVEL=INFO
PID_PREFIX_STRATEGY=true
```

**L'app fonctionne 100% offline SANS ANTHROPIC_API_KEY** pour tout sauf :
- Ask Your Data → fallback : affiche juste le SQL
- SBAR Generator → fallback : alerte générique
- Auto-Doc Generator → fallback : rapport template
- Anomaly Explainer → fallback : explication hardcodée

---

<a name="contraintes"></a>

## 10. CONTRAINTES IMPORTANTES

1. L'app doit fonctionner **100% OFFLINE** — aucun appel API externe requis pour le core.
2. Le fichier 1Hz (9.99MB) ne doit **JAMAIS** être chargé entièrement en mémoire — `chunksize=5000`.
3. Chaque valeur modifiée automatiquement doit être loggée dans **tbAuditLog**.
4. L'app ne doit **jamais crasher** sur un fichier mal formé — toujours try/except + continuer.
5. Le schéma SQL cible est dans `DB/CreateImportTables.sql`. `DB/Hack2026.bak` contient les données d'exemple.
6. Tester avec les deux dossiers :
   - dirty/ → INPUT à nettoyer
   - clean/ → VALIDATION de votre output (comparer résultats)
7. Traiter aussi les **28 fichiers du dossier split** (4 cliniques × 7 types) incluant XLSX et PDF.
8. Parser IID-SID-ITEM.csv avec `on_bad_lines='skip'` (erreur quoting ligne 4481).
9. Gérer les **deux formats epaAC** : SAP codes (clean) et noms allemands (dirty/split).
10. Détecter les fichiers par **colonnes, pas par nom** — les noms diffèrent entre clean et dirty.
11. Mapper **patient_id + datetime → case_id** quand case_id absent.
12. Gérer les PID dupliqués avec **préfixe source** (LAB_, MOT_, EPA_, MED_, NUR_).

---

<a name="ordre"></a>

## 11. ORDRE D'IMPLÉMENTATION

### PRIORITÉS — Ce qui est OBLIGATOIRE en premier

```
OBLIGATOIRE (faire en premier) :
  ✅ 1. Parser IID-SID-ITEM.csv (on_bad_lines='skip') → dictionnaire de décodage SAP
  ✅ 2. Restaurer DB/Hack2026.bak → voir les données cibles attendues
  ✅ 3. Ingestion multi-format : CSV + XLSX + PDF (pdfplumber pour clinic_4_nursing.pdf)
  ✅ 4. Ingestion des 4 cliniques (28 fichiers split) + 8 sources de base
  ✅ 5. Détection par contenu/colonnes (pas par nom de fichier)
  ✅ 6. Validation & nettoyage (dates, valeurs, genres, IDs, doublons)
  ✅ 7. Gestion PID dupliqués avec préfixe source
  ✅ 8. Mapping vers 7 tables SQL (avec décodage SAP via IID-SID-ITEM.csv pour epaAC)
  ✅ 9. Mapping patient_id + datetime quand case_id manquant
  ✅ 10. Export SQLite + tbAuditLog
  ✅ 11. Dashboard 5 pages (Overview, Quality, Patient, Alertes, Correction)
  ✅ 12. Validation : comparer output dirty avec données clean

BONUS si le temps le permet :
  ⭐ NLP nursing notes
  ⭐ Anomaly detection cross-dataset
  ⭐ Multi-agent system
  ⭐ SBAR alerts
  ⭐ Patient Convergence Score
  ⭐ Features 1-11
```

### Phase par phase — Backend

```
PHASE 0 — SETUP
  0.1 Structure dossiers medmap/
  0.2 requirements.txt
  0.3 config/ (settings, clinical_rules, gender_mapping, schema_mapping)
  0.4 .env + Dockerfile + docker-compose.yml
  0.5 api/main.py squelette + dependencies.py

PHASE 1 — INGESTION
  1.1 DataIngester classe + load(filepath)
  1.2 Auto-détection délimiteur + encodage
  1.3 Détection type fichier par colonnes
  1.4 Ingestion 8 sources de base (CSV, XLSX)
  1.5 Ingestion 28 fichiers split (CSV + XLSX + PDF)
  1.6 IID-SID-ITEM.csv parsing
  1.7 Correction delimiter mismatch epaAC-Data-3
  1.8 1Hz en chunks (chunksize=5000)

PHASE 2 — VALIDATION & NETTOYAGE
  2.1 AuditLog DataFrame pour chaque valeur
  2.2 Valeurs manquantes
  2.3 Normalisation dates (5 passes)
  2.4 Validation clinique (17 paramètres)
  2.5 Normalisation genre
  2.6 Nettoyage IDs + gestion PID dupliqués (préfixes)
  2.7 Mapping patient_id + datetime → case_id
  2.8 Doublons
  2.9 Delimiter mismatch
  2.10 Flags labo

PHASE 3 — MAPPING
  3.1-3.9 Mapping vers 7 tables (voir Module 3)

PHASE 4 — EXPORT SQL
  4.1 SQLite (adapter T-SQL)
  4.2 Insertion ordre FK
  4.3 tbAuditLog
  4.4 tbDataPassport (bonus)

PHASE 5 — API FASTAPI
  5.1-5.9 Les 25 endpoints (voir section 6)

PHASE 6 — VALIDATION
  6.1 dirty → pipeline → comparer avec clean
  6.2 split → pipeline → vérifier mapping

PHASE 7+ — BONUS
  7. NLP (pipeline/nlp.py)
  8. Anomaly detection (pipeline/anomaly.py)
  9. Agents (pipeline/agents/)
  10. Features restantes (Ward Scoreboard, Streaming Viz, etc.)
  11. Docker build + test
```

### Phase par phase — Frontend

```
Phase 0 — Setup (30 min)
  Copier starter, nettoyer Clerk/Sentry, créer contracts.ts, api.ts, mock-data.ts

Phase 1 — Overview (1.5h)
Phase 2 — Patient View (1.5h)
Phase 3 — Alertes SBAR (45 min)
Phase 4 — Agent Orchestra (1h)
Phase 5 — Data Quality (1h)
Phase 6 — Time Travel (45 min)
Phase 7 — Corrections (45 min)
Phase 8 — Ask Your Data (30 min)
Phase 9 — ROI Calculator (30 min)
```

### Commandes

```bash
# Backend
cd medmap
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn api.main:app --reload --port 8000
# Swagger : http://localhost:8000/docs

# Frontend
cd frontend
npm install
npm run dev
# Dashboard : http://localhost:3000

# Docker (démo finale)
docker-compose up --build
```

---

*Dernière mise à jour : 19 mars 2026*
*Fusion de : MEDMAP_PROMPT.md + PROMPT_BACKEND.md + PROMPT_FRONTEND_REACT.md + RESUME_PROJET.md*
*Corrections intégrées : Discord + vérification complète repo GitHub*
