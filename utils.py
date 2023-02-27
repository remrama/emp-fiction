"""Helper functions."""
import json
from pathlib import Path

import pandas as pd


def load_config():
    with open("./config.json", "r", encoding="utf-8") as jsonfile:
        config = json.load(jsonfile)
    config["bids_root"] = Path(config["bids_root"]).expanduser()
    return config

def load_participant_file():
    config = load_config()
    path = config["bids_root"] / "participants.tsv"
    return pd.read_csv(path, sep="\t", index_col="participant_id")

def export_sidecar(obj, filepath):
    json_filepath = Path(filepath).with_suffix(".json")
    with open(json_filepath, "w", encoding="utf-8") as fp:
        json.dump(obj, fp, indent=4, sort_keys=False, ensure_ascii=True)


# def load_all_data(exclude=False):
#     """Load and merge survey data, BCT score, EAT scores
#     so each participant is 1 row.
#     """
#     import json
#     import os
#     import pandas as pd

#     root_dir = load_config().bids_root
#     survey_path = os.path.join(root_dir, "phenotype", "debriefing.tsv")
#     bct_path = os.path.join(root_dir, "derivatives", "pandas", "task-bct_agg-sub_rrate.tsv")
#     bct2_path = os.path.join(root_dir, "derivatives", "pandas", "task-bct_rrate.tsv")
#     eat_pre_path = os.path.join(root_dir, "derivatives", "pandas", "task-eat_acq-pre_agg-sub_corrs.tsv")
#     eat_post_path = os.path.join(root_dir, "derivatives", "pandas", "task-eat_acq-post_agg-sub_corrs.tsv")

#     sidecar_path = survey_path.replace(".tsv", ".json")
#     with open(sidecar_path, "r") as f:
#         survey_sidecar = json.load(f)

#     participants = load_participant_file()
#     survey = pd.read_csv(survey_path, sep="\t")
#     bct = pd.read_csv(bct_path, sep="\t")
#     bct2 = pd.read_csv(bct2_path, sep="\t")
#     eat_pre = pd.read_csv(eat_pre_path, sep="\t")
#     eat_post = pd.read_csv(eat_post_path, sep="\t")

#     survey["participant_id"] = survey["participant_id"].map(lambda x: f"sub-{x:03d}")
#     bct2.columns = [ c if c == "participant_id" else f"rrate-{c}" for c in bct2 ]

#     df = participants.merge(survey, on="participant_id"
#         ).merge(bct, on="participant_id", how="left"
#         ).merge(bct2, on="participant_id", how="left"
#         ).merge(eat_pre, on="participant_id"
#         ).merge(eat_post, on="participant_id", suffixes=("_pre", "_post"))

#     # Add delta (difference) columns for all the EAT measures.
#     for col in df:
#         if col.endswith("_post"):
#             pre_col = col.replace("_post", "_pre")
#             diff_col = col.replace("_post", "_delta")
#             df[diff_col] = df[col].sub(df[pre_col])

#     if exclude:
#         df = df[df["included"]].reset_index(drop=True)

#     return df, survey_sidecar


def stack_raw_task_data(task_label):
    import os
    import pandas as pd
    walk_dir = os.path.join(load_config().bids_root)
    file_list = []
    for root, dirs, files in os.walk(walk_dir):
        for name in files:
            if f"task-{task_label}" in name and name.endswith("_beh.tsv"):
                full_path = os.path.join(root, name)
                file_list.append(full_path)
    file_list = sorted(file_list)
    df_list = []
    for file in file_list:
        _df = pd.read_csv(file, sep="\t")
        if "acq-" in file:
            sub, _, acq = filename2labels(file)
            index = pd.MultiIndex.from_tuples([(sub, acq)]*len(_df), names=["participant_id", "acquisition_id"])
        else:
            sub, _ = filename2labels(file)
            index = pd.Index([sub]*len(_df), name="participant_id")
        _df.index = index
        df_list.append(_df)
    df = pd.concat(df_list, ignore_index=False)
    return df


def get_true_timecourses(video_id):
    """Load the SEND actor and crowd ratings of emotions"""
    import csv
    import zipfile
    from io import TextIOWrapper

    with open("db_pword.txt", "rb") as f:
        db_pword = f.read()
    ratings_zip_path = "../stimuli/SENDv1_featuresRatings_pw.zip"
    actor_id = video_id[2:5] # the actor ID
    actor_nid = video_id[-1] # specifies which of N videos from this actor
    path_basename = f"target_{actor_id}_{actor_nid}_normal.csv"
    # Roam through the train/test/valid files to see where this actor's ratings are located.
    with zipfile.ZipFile(ratings_zip_path, "r") as z:
        z.setpassword(db_pword)
        for fn in z.namelist():
            if fn.startswith("ratings") and fn.endswith(path_basename):
                with z.open(fn) as f:
                    reader = csv.DictReader(TextIOWrapper(f, "utf-8"), delimiter=",")
                    actor_ratings = [ float(row[" rating"]) for row in reader ]
                # same for crowd
                fn_crowd = fn.replace("target_", "results_"
                    ).replace("_normal", ""
                    ).replace("target", "observer_EWE")
                with z.open(fn_crowd) as f:
                    reader = csv.DictReader(TextIOWrapper(f, "utf-8"), delimiter=",")
                    crowd_ratings = [ float(row["evaluatorWeightedEstimate"]) for row in reader ]
                return actor_ratings, crowd_ratings

# def save_raw_subject_files(basename, subdir=None):
#     import os
#     bids_root = load_config().bids_root
#     export_dir = f"sub-"
#     for name in basename_list:
#         ids = parse_bids_basename(name, as_dict=True)
#         os.path.join(bids_root, )


def load_participant_palette(separate_by_task=True):
    """Load from utils for not just convenience
    but also to make sure colors are consistent across
    plots (ie, even if a subj is removed from a later analysis).
    So load earliest possible dataframe here.
    glasbey colormaps: https://colorcet.holoviz.org/user_guide/Categorical.html
    """
    import colorcet as cc
    participants = load_participant_file()
    if separate_by_task:
        cond1_participants = participants.query("intervention=='svp'").index.unique()
        cond2_participants = participants.query("intervention=='bct'").index.unique()
        cond1_palette = { p: cc.cm.glasbey_warm(i) for i, p in enumerate(cond1_participants) }
        cond2_palette = { p: cc.cm.glasbey_cool(i) for i, p in enumerate(cond2_participants) }
        assert 0 == len(cond1_palette.keys() & cond2_palette.keys()), "Should not have overlapping subjects."
        participant_palette = cond1_palette | cond2_palette
    else: # glasbey_bw or glasbey_dark
        all_participants = participants.index.unique()
        participant_palette = { p: cc.cm.glasbey_dark(i) for i, p in enumerate(all_participants) }
    return participant_palette


def save_matplotlib(png_path, hires_extension="pdf"):
    """Saves out hi-resolution matplotlib figures.
    Assumes there is a "hires" subdirectory within the path
    of the filename passed in, which must be also be a png filename.
    """
    assert png_path.endswith(".png"), "Expected .png filename"
    import matplotlib.pyplot as plt
    png_dir, png_bname = os.path.split(png_path)
    png_bname_noext, _ = os.path.splitext(png_bname)
    hires_dir = os.path.join(png_dir, "hires")
    hires_bname = png_bname.replace(".png", f".{hires_extension}")
    hires_path = os.path.join(hires_dir, hires_bname)
    make_pathdir_if_not_exists(hires_path)
    plt.savefig(png_path)
    plt.savefig(hires_path)
    plt.close()

def load_matplotlib_settings():
    from matplotlib.pyplot import rcParams
    # rcParams["figure.dpi"] = 600
    rcParams["savefig.dpi"] = 600
    rcParams["interactive"] = True
    rcParams["figure.constrained_layout.use"] = True
    rcParams["font.family"] = "Times New Roman"
    # rcParams["font.sans-serif"] = "Arial"
    rcParams["mathtext.fontset"] = "custom"
    rcParams["mathtext.rm"] = "Times New Roman"
    rcParams["mathtext.cal"] = "Times New Roman"
    rcParams["mathtext.it"] = "Times New Roman:italic"
    rcParams["mathtext.bf"] = "Times New Roman:bold"
    rcParams["font.size"] = 8
    rcParams["axes.titlesize"] = 8
    rcParams["axes.labelsize"] = 8
    rcParams["axes.labelsize"] = 8
    rcParams["xtick.labelsize"] = 8
    rcParams["ytick.labelsize"] = 8
    rcParams["axes.linewidth"] = 0.8 # edge line width
    rcParams["axes.axisbelow"] = True
    rcParams["axes.grid"] = True
    rcParams["axes.grid.axis"] = "y"
    rcParams["axes.grid.which"] = "major"
    rcParams["axes.labelpad"] = 4
    rcParams["xtick.top"] = True
    rcParams["ytick.right"] = True
    rcParams["xtick.direction"] = "in"
    rcParams["ytick.direction"] = "in"
    rcParams["grid.color"] = "gainsboro"
    rcParams["grid.linewidth"] = 1
    rcParams["grid.alpha"] = 1
    rcParams["legend.frameon"] = False
    rcParams["legend.edgecolor"] = "black"
    rcParams["legend.fontsize"] = 8
    rcParams["legend.title_fontsize"] = 8
    rcParams["legend.borderpad"] = .4
    rcParams["legend.labelspacing"] = .2 # the vertical space between the legend entries
    rcParams["legend.handlelength"] = 2 # the length of the legend lines
    rcParams["legend.handleheight"] = .7 # the height of the legend handle
    rcParams["legend.handletextpad"] = .2 # the space between the legend line and legend text
    rcParams["legend.borderaxespad"] = .5 # the border between the axes and legend edge
    rcParams["legend.columnspacing"] = 1 # the space between the legend line and legend text
