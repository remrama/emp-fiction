"""Convert raw Qualtrics data to phenotype and behavioral dirs?
"""
import pyreadstat

import utils

config = utils.load_config()
bids_root = config["bids_root"]
phenotype_dir = bids_root / "phenotype"
phenotype_dir.mkdir(exist_ok=True)

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


