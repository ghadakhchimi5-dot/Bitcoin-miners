# R helpers for Phase 4 (VAR, Granger, Johansen, Engle-Granger, VECM); mirror src/multivariate.py.

suppressPackageStartupMessages({
  library(vars)
  library(urca)
})

# Pre-pivot (strictly before) / post-pivot (from the pivot day) / full, as in Python's period_slices().
period_rows <- function(x, pivot) {
  d <- zoo::index(x); p <- as.Date(pivot)
  list("full" = x, "pre-pivot" = x[d < p], "post-pivot" = x[d >= p])
}

# Pairwise Granger test inside a VAR(p): F test that the p lags of `cause` are zero in the equation of `effect`.
# Single-equation F (df2 = n - number of regressors); Python's statsmodels uses a system Wald F with a larger df2,
# so p-values can differ slightly in the 3rd decimal.
granger_pair <- function(df, cause, effect, p = 1) {
  n <- nrow(df)
  lagged <- do.call(cbind, lapply(1:p, function(l) {
    m <- df[(p - l + 1):(n - l), , drop = FALSE]; colnames(m) <- paste0(colnames(df), "_l", l); m }))
  y <- df[(p + 1):n, effect]
  full <- lm(y ~ ., data = as.data.frame(lagged))
  keep <- !grepl(paste0("^", cause, "_l"), colnames(lagged))
  restr <- lm(y ~ ., data = as.data.frame(lagged[, keep, drop = FALSE]))
  a <- anova(restr, full)
  c(F = a$F[2], p_value = a$`Pr(>F)`[2])
}

# Johansen trace and max-eigenvalue for a pair with an unrestricted constant (ecdet = "none"), K = k_ar_diff + 1.
johansen_pair <- function(y, k_ar_diff = 1) {
  tr <- ca.jo(y, type = "trace", ecdet = "none", K = k_ar_diff + 1, spec = "transitory")
  me <- ca.jo(y, type = "eigen", ecdet = "none", K = k_ar_diff + 1, spec = "transitory")
  # urca lists statistics from r <= 1 down to r = 0; reorder to r = 0, r = 1.
  ts_ <- rev(tr@teststat); cv_tr <- tr@cval[2:1, "5pct"]
  me_ <- rev(me@teststat); cv_me <- me@cval[2:1, "5pct"]
  rank_tr <- if (ts_[1] < cv_tr[1]) 0 else if (ts_[2] < cv_tr[2]) 1 else 2
  rank_me <- if (me_[1] < cv_me[1]) 0 else if (me_[2] < cv_me[2]) 1 else 2
  data.frame(trace_r0 = ts_[1], cv95_trace_r0 = cv_tr[1], trace_r1 = ts_[2], cv95_trace_r1 = cv_tr[2],
             maxeig_r0 = me_[1], cv95_maxeig_r0 = cv_me[1], rank_trace = rank_tr, rank_maxeig = rank_me)
}

# Engle-Granger statistic: ADF t-statistic (no deterministic term) on OLS residuals, lags by AIC, same maximum lag
# as statsmodels' default (12 * (n/100)^(1/4)). The p-value is not recomputed here; the statistic is compared to Python's.
eg_stat <- function(y, x) {
  e <- residuals(lm(y ~ x))
  maxlag <- floor(12 * (length(e) / 100)^(1 / 4))
  ur.df(e, type = "none", lags = maxlag, selectlags = "AIC")@teststat[1]
}

half_life <- function(alpha) ifelse(alpha > -1 & alpha < 0, log(0.5) / log(1 + alpha), NA)
