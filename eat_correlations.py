"""
Get correlation scores for Empathic Accuracy Task
and export a single tsv with all the scores and participant IDs and conditions.
"""
import numpy as np
import pandas as pd
from scipy import stats

from bids import BIDSLayout

import utils



config = utils.load_config()

export_path = config["bids_root"] / "derivatives" / "task-eat_corrs.tsv"


# Load all Empathic Accuracy Tasks.
layout = BIDSLayout(config["bids_root"], validate=False)

bids_files = layout.get(task="eat", datatype="beh", suffix="beh", extension=".tsv")

df = pd.concat([ bf.get_df().assign(**bf.get_entities()) for bf in bids_files ])
df = df.drop(columns=["datatype", "extension", "suffix", "task"])
df["subject"] = df["subject"].radd("sub-")
# df = df.set_index(["subject", "acquisition", "trial_number", "stimulus"])


def get_correlation(ratings1, ratings2):
    # trim to account for minor size differences
    shortest_length = min((map(len, [ratings1, ratings2])))
    ratings1 = ratings1[:shortest_length]
    ratings2 = ratings2[:shortest_length]
    # ratings1 = np.convolve(ratings1, np.ones(4), "valid") / 4
    # ratings2 = np.convolve(ratings2, np.ones(4), "valid") / 4
    ratings1_z = stats.zscore(ratings1, nan_policy="raise")
    ratings2_z = stats.zscore(ratings2, nan_policy="raise")
    r, _ = stats.spearmanr(ratings1_z, ratings2_z)
    rz = np.arctanh(r)
    return rz

def get_empathy_accuracy_scores(ser):
    participant_timecourse = ser.tolist()
    _, _, video_id = ser.name
    # grab true timecourses from SEND dataset
    actor_timecourse, crowd_timecourse = utils.get_true_timecourses(video_id)
    # correlate
    r_actor = get_correlation(actor_timecourse, participant_timecourse)
    r_crowd = get_correlation(crowd_timecourse, participant_timecourse)
    return (r_actor, r_crowd)


corrs = (df
    # .reset_index()
    .groupby(["subject", "acquisition", "stimulus"])["response"]
    .apply(get_empathy_accuracy_scores)
    .apply(pd.Series)
    .rename(columns={0: "actor_correlation", 1: "crowd_correlation"})
)


utils.export_table(corrs, export_path)


# Summarize pre/post for each subject, export in long and wide format.

long_ = corrs.groupby(["subject", "acquisition"]).mean().sort_index(ascending=[True, False])
wide_ = long_["actor_correlation"].unstack().rename_axis(columns=None).sort_index(axis=1, ascending=False)

pheno = pd.read_table(config["bids_root"] / "phenotype" / "survey.tsv")
pheno["subject"] = pheno["participant_id"].map("sub-{:03d}".format)

long_ = (pheno[["subject", "Condition"]].merge(long_, on="subject").rename(columns={"Condition": "condition"}))
wide_ = (pheno[["subject", "Condition"]].merge(wide_, on="subject").rename(columns={"Condition": "condition"}))


utils.export_table(long_, export_path.with_stem("task-eat_corrs-long"))
utils.export_table(wide_, export_path.with_stem("task-eat_corrs-wide"))

