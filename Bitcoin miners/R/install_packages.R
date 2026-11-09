# Install every R package the project needs (run once: Rscript R/install_packages.R).
# Why one script: the brief requires notebooks that run on a clean machine with documented packages.

repos <- "https://cloud.r-project.org"

pkgs <- c(
  # Phase 1 (data)
  "yaml", "xts", "zoo", "tsibble", "dplyr", "rmarkdown", "knitr",
  # Later phases (installed now so the environment is fixed from the start)
  "forecast", "tseries", "urca", "vars", "rugarch", "FinTS", "lmtest", "ggplot2"
)

missing <- setdiff(pkgs, rownames(installed.packages()))
if (length(missing) > 0) install.packages(missing, repos = repos)

# Print versions so they can be copied into the report / README.
for (p in pkgs) cat(sprintf("%-10s %s\n", p, as.character(packageVersion(p))))
