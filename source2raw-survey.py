"""Convert raw Qualtrics data to phenotype and behavioral dirs?
"""
import pyreadstat

import utils

config = utils.load_config()
bids_root = config["bids_root"]
phenotype_dir = bids_root / "phenotype"
phenotype_dir.mkdir(exist_ok=True)

export_path = phenotype_dir / "survey.tsv"


filepaths = bids_root.joinpath("sourcedata").glob("*.sav")
fp = next(filepaths)
assert not list(filepaths), "There should only be 1 .sav file in `sourcedata`."

df, meta = pyreadstat.read_sav(fp)


# Exclude any submissions prior to the original study advertisement.
# Convert to the Qualtrics timestamps from MST to CST since that's the time I have it in.
for col in ["StartDate", "EndDate", "RecordedDate"]:
    df[col] = df[col].dt.tz_localize("US/Mountain").dt.tz_convert("US/Central")

# Sort for readability
df = df.sort_values("StartDate")


# That should handle all the "previews" from this column, but check.
df = df.query("DistributionChannel=='anonymous'")

assert df["Status"].eq(0).all(), "All surveys should have come from the anonymous link."

df = df.query("Finished==1")
df = df.query("Progress==100") # redundant I think

# Can't see how these would be off but w/e just check
assert df["ResponseId"].is_unique, "These should all be unique."
assert df["UserLanguage"].eq("EN").all(), "All languages should be English."

# Remove default Qualtrics columns
drop_columns = [
    "StartDate", "EndDate", "RecordedDate",         # Qualtrics stuff we're done with.
    "Status", "DistributionChannel", "Progress",    # Qualtrics stuff we're done with.
    "Finished", "ResponseId", "UserLanguage",       # Qualtrics stuff we're done with.
    "Duration__in_seconds_",
]
df = df.drop(columns=drop_columns)

# Remove participants who did not consent or are ineligible.
df = df[df["Consent_Id"].str.len().gt(0)]

# Then remove Consent columns
consent_cols = [c for c in df if c.startswith("Consent")]
df = df.drop(columns=consent_cols)

# Convert age to a number
df["Age"] = df["Age"].astype(int)
df = df.query("Age >= 18")


df = df.rename(columns={
        "Q118": "participant_id",
        "Q1_1": "ArousalPre",
        "Q2_1": "PleasurePre",
        "Q14_1": "ArousalPost",
        "Q15_1": "PleasurePost",
        "Q37": "Letter1",
        "Q42": "Letter2",
    }
)

# Rename some participant IDs that were entered wrong in survey
df["participant_id"] = df["participant_id"].replace({
    "3127": "17",
    "3314": "26",
    "3309": "27",
})

df = df[df["participant_id"].str.len().gt(0)]
df["participant_id"] = df["participant_id"].astype(int)
participants = utils.load_participant_file().index.tolist()
df = df[df["participant_id"].isin(participants)]
df = df.set_index("participant_id")


################################################################################
# SEPARATE QUESTIONNAIRES
################################################################################

# Demographic stuff
demographic_columns = [
    "Age",
    "Gender",

    # # Consolidate these
    # "Race1_1", "Race1_2", "Race1_3", "Race1_4", "Race1_5", "Race1_6", "Race1_7",
    # "Race2",

    # "IRI", "MWQ", "ART",
    
    "DRF", "DreamEmoTone", "DreamEmoIntensity",
    "NMRF", "NMD", "LDRF", "DreamSharing", "DreamReceiving",
    "Condition",
    # # Consolidate these
    # "Strategy_pre_1",
    # "Strategy_pre_2",
    # "Strategy_pre_3",
    # "Strategy_pre_4",
    # "Strategy_post_1",
    # "Strategy_post_2",
    # "Strategy_post_3",
    # "Strategy_post_4",
]

# "Letter1",
# "Letter2",
# "NFictionRecallInstr",
# "FictionRecallInstr",
# "Suspicion",

timing_columns = [c for c in df if "Timer" in c]
timing = df[timing_columns].copy()
df = df.drop(columns=timing_columns)

demogr = df[demographic_columns].copy()
demogr.to_csv(export_path, index=True, na_rep="n/a", sep="\t")


# meta.variable_value_labels


################################################################################
# SCORING QUESTIONNAIRES
################################################################################

# Score Mind Wandering Questionnaire
columns = [f"MWQ_{i + 1}" for i in range(5)]
df["MWQ"] = df[columns].sum(axis=1)
df = df.drop(columns=columns)

# Score IRI
columns = [f"IRI_{i + 1}" for i in range(28)]
df["IRI"] = df[columns].sum(axis=1)
df = df.drop(columns=columns)

# Score Author Recognition Test
columns = [f"AuthorRecog_{i + 1}" for i in range(65)]
df["ART"] = df[columns].fillna(0).sum(axis=1)
df = df.drop(columns=columns)

# Score State Empathy Scale both pre and post.
columns = [f"SES_pre_{i + 1}" for i in range(12)]
df["pre.SES"] = df[columns].sum(axis=1)
df = df.drop(columns=columns)

columns = [f"SES_post_{i + 1}" for i in range(12)]
df["post.SES"] = df[columns].sum(axis=1)
df = df.drop(columns=columns)



# Export
df.to_csv(export_path, index=True, na_rep="n/a", sep="\t")
