# teacher_consistency_analysis_book_page.py
# Consistency for Chinese (teachers): pages identified by (book_id, page_number)

import pandas as pd
import numpy as np
from scipy.stats import rankdata
import pingouin as pg

# -------- 1) Load raw CSV --------
df = pd.read_csv("exp_1_teacher_chinese_raw.csv")

# Keep PAGE-level only
page_df = df[df["question_scope"] == "PAGE"].copy()

# Basic sanity print
n_raters = page_df["rater_id"].nunique()
n_books  = page_df["book_id"].nunique()
n_pages  = page_df[["book_id","page_number"]].drop_duplicates().shape[0]
print(f"Loaded PAGE-level ratings: {len(page_df)} rows | raters={n_raters} | books={n_books} | book-pages={n_pages}")

# -------- 2) Average the 3 PAGE items per (book_id, page_number, rater_id) --------
# Items are those PAGE questions: image correspondence, gloss accuracy, translation accuracy
page_means = (
    page_df.groupby(["book_id","page_number","rater_id"], as_index=False)["likert"]
           .mean()
           .rename(columns={"likert":"mean_rating"})
)

# Pivot to (book_id, page_number) x rater matrix
pivot = page_means.pivot(index=["book_id","page_number"], columns="rater_id", values="mean_rating")

# Drop incomplete targets (any missing rater)
pivot = pivot.dropna(axis=0, how="any")

n_targets, m_raters = pivot.shape
print(f"Analysing {n_targets} book-pages rated by all {m_raters} teachers (complete cases).")

# -------- 3) Kendall’s W across raters --------
# W uses ranks per rater; targets are rows (book-page)
ranks = pivot.apply(rankdata, axis=0)               # rank each rater's column
Rj = ranks.sum(axis=1)                              # sum of ranks per target
n, m = ranks.shape
S = np.sum((Rj - np.mean(Rj))**2)
W = 12 * S / (m**2 * (n**3 - n))

print(f"\nKendall’s W (book-page targets): {W:.3f}")
print("Benchmarks: 0–0.2 slight | 0.2–0.4 fair | 0.4–0.6 moderate | 0.6–0.8 substantial | >0.8 almost perfect")

# ------- 3a) chi-square significance (large n will almost always be p<.001)
##from scipy.stats import chi2
##
##chi2_stat = W * m * (n - 1)
##p_value = 1 - chi2.cdf(chi2_stat, df=n-1)
##print(f"Approx. χ²({n-1}) = {chi2_stat:.1f}, p = {p_value:.3g}")

# -------- 4) ICC(2,k): two-way random, absolute agreement, average of k raters --------
long_df = pivot.reset_index().melt(id_vars=["book_id","page_number"],
                                   var_name="rater", value_name="score")
# Combine book_id & page_number into a single target label for pingouin
long_df["target"] = long_df["book_id"].astype(str) + "_" + long_df["page_number"].astype(str)

icc_tbl = pg.intraclass_corr(data=long_df, targets="target", raters="rater", ratings="score")
icc2k = icc_tbl.loc[icc_tbl["Type"]=="ICC2k", ["Type","ICC","CI95%"]]

print("\nICC (two-way random, absolute agreement, average raters):")
print(icc2k.to_string(index=False))

# -------- 5) Optional instrument check (Cronbach’s alpha across PAGE items) --------
# For the questionnaire (not rater agreement): compute alpha across the three PAGE items.
# Build per-(book_id,page,rater) wide frame with the 3 item scores.
items = page_df.pivot_table(index=["book_id","page_number","rater_id"],
                            columns="question_text", values="likert", aggfunc="mean")

# Ensure we only keep rows where all three items are present
items = items.dropna(axis=0, how="any")

# Pingouin expects columns = items; compute alpha overall by stacking across book-pages & raters
# (If you prefer per-rater alphas, groupby 'rater_id' and run pg.cronbach_alpha on each subset.)
alpha, ci = pg.cronbach_alpha(items)
print(f"\nCronbach’s α across PAGE items (gloss, translation, image): {alpha:.3f}  CI95%={ci}")

# -------- 6) Quick descriptive summary per rater (useful to spot any outlier rater) --------
print("\nDescriptive statistics per rater (mean rating across book-pages):")
print(pivot.describe().T[["mean","std","min","max"]])
