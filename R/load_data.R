# R helpers: locate the project, read config.yaml, load the processed panel as xts.
# Every R notebook sources this file so R and Python share one dataset and one config.

suppressPackageStartupMessages({
  library(yaml)
  library(xts)
})

# Walk up from the working directory until config.yaml is found (relative paths only).
project_root <- function(start = getwd()) {
  d <- normalizePath(start, winslash = "/")
  repeat {
    if (file.exists(file.path(d, "config.yaml"))) return(d)
    parent <- dirname(d)
    if (parent == d) stop("config.yaml not found in any parent folder")
    d <- parent
  }
}

load_config <- function(root = project_root()) {
  yaml::read_yaml(file.path(root, "config.yaml"))
}

# Processed panel as an xts object indexed by trading date (the same CSV Python writes).
load_panel <- function(root = project_root()) {
  cfg <- load_config(root)
  f <- file.path(root, cfg$paths$processed, "panel.csv")
  df <- read.csv(f, check.names = FALSE, stringsAsFactors = FALSE)
  xts::xts(as.matrix(df[, -1]), order.by = as.Date(df$Date))
}

# Chronological split using the dates stored in config.yaml by notebook 01 (never random).
split_panel <- function(x, cfg = load_config()) {
  list(train = x[paste0("/", cfg$split$train_end)],
       test  = x[paste0(cfg$split$test_start, "/")])
}

# Same fingerprint as src/data.py::summary_stats (sd with n-1, like pandas).
summary_stats <- function(x, columns) {
  m <- zoo::coredata(x[, columns])
  data.frame(column = columns,
             count = colSums(!is.na(m)),
             mean = colMeans(m, na.rm = TRUE),
             std = apply(m, 2, sd, na.rm = TRUE),
             min = apply(m, 2, min, na.rm = TRUE),
             max = apply(m, 2, max, na.rm = TRUE),
             row.names = NULL)
}
