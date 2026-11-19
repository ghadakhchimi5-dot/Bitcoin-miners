# R helpers for Phase 3 (ARIMA): same residual tests as src/arima.py so both languages are compared line by line.

suppressPackageStartupMessages({
  library(forecast)
  library(tseries)
  library(FinTS)
})

# Brief §3.1: independence (Ljung-Box), normality (Jarque-Bera, Shapiro-Wilk), ARCH-LM, each with H0 and a verdict.
# fitdf = p + q corrects the Ljung-Box degrees of freedom; the first residual of a d = 1 model is dropped by the caller.
resid_diagnostics <- function(e, fitdf = 0, lags = c(5, 10, 20)) {
  rows <- list()
  add <- function(test, param, h0, stat, p) rows[[length(rows) + 1]] <<- data.frame(
    test = test, parameter = param, H0 = h0, statistic = unname(stat), p_value = unname(p))
  for (m in lags) {
    b <- Box.test(e, lag = m, type = "Ljung-Box", fitdf = fitdf)
    add("Ljung-Box", paste("lag", m), "no autocorrelation up to lag m", b$statistic, b$p.value)
  }
  b2 <- Box.test(e^2, lag = 10, type = "Ljung-Box")
  add("Ljung-Box on e2", "lag 10", "no autocorrelation of squares", b2$statistic, b2$p.value)
  ba <- Box.test(abs(e), lag = 10, type = "Ljung-Box")
  add("Ljung-Box on |e|", "lag 10", "no autocorrelation of absolute values", ba$statistic, ba$p.value)
  jb <- tseries::jarque.bera.test(e)
  add("Jarque-Bera", "", "normal residuals", jb$statistic, jb$p.value)
  sw <- shapiro.test(e)
  add("Shapiro-Wilk", "", "normal residuals", sw$statistic, sw$p.value)
  for (m in c(5, 10)) {
    a <- FinTS::ArchTest(e, lags = m, demean = TRUE)
    add("ARCH-LM", paste("lag", m), "no ARCH effect", a$statistic, a$p.value)
  }
  out <- do.call(rbind, rows)
  out$conclusion <- ifelse(out$p_value < 0.05, "reject H0", "H0 not rejected")
  out
}
