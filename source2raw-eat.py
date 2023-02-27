"""
Convert raw Empathic Accuracy Task data (i.e., PsychoPy output)
into more useful and cleaner tsv files.
"""
import os
import json
from itertools import repeat
import pandas as pd

import utils

config = utils.load_config()
bids_root = config["bids_root"]
global_metadata = config["global_bids_metadata"]
practice_video_id = config["practice_video_id"]
sample_rate_hz = config["eat_sample_rate_hz"]
sample_rate_s = 1 / sample_rate_hz




task_metadata = {
    "TaskName": "Empathy Accuracy Task",
    "TaskDescription": "A behavioral measure of empathy. See Ong et al., 2019 for details (https://doi.org/10.1109/TAFFC.2019.2955949 and https://github.com/desmond-ong/TAC-EA-model)",
    "Instructions": [
        "As you watch the following videos, continuously rate how positive or negative you believe the speaker is feeling at every moment."
    ]
}

column_metadata = {
    "trial_number": {
        "LongName": "Trial number",
        "Description": "Trial number"
    },
    "stimulus": {
        "LongName": "Video stimulus",
        "Description": "Video ID (in reference to SENDv1 dataset)"
    },
    "time": {
        "LongName": "Time of sample",
        "Description": "Responses were made continuously, but here resampled to 2 Hz",
        "Units": "seconds",
    },
    "response": {
        "LongName": "Response at current sample",
        "Description": "The slider position at the given sample time"
    }
}

column_names = list(column_metadata.keys())

sidecar = task_metadata | global_metadata | column_metadata


filepaths = bids_root.joinpath("sourcedata").glob("*/*.json")

for fp in filepaths:
    with open(fp, "r", encoding="utf-8") as f:
        subject_data = json.load(f)
    # remove practice trial
    subject_data = { k: v for k, v in subject_data.items() if k != practice_video_id }
    # wrangle
    trials = [ [repeat(i+1, len(v)), repeat(k, len(v)),
                [ sample_rate_s*j for j in range(len(v)) ], v]
        for i, (k, v) in enumerate(subject_data.items()) ]
    df = pd.concat([ pd.DataFrame(t).T for t in trials ])
    sub, ses, task = fp.stem.split("_")
    filename = (
        # BIDS-compatibility
        fp.with_stem(fp.stem + "_beh").with_suffix(".tsv")
        # Remove session ID because nobody did two sessions.
        .name.replace("_ses-001", "")
        .replace("-eatA", "-eat_acq-pre")
        .replace("-eatB", "-eat_acq-post")
    )
    export_path = bids_root / sub / "beh" / filename
    export_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(export_path, header=column_names, float_format="%.0f", index=False, sep="\t")
    utils.export_sidecar(sidecar, export_path)
