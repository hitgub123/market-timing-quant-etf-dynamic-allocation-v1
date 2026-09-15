# Phase 8B-2 DSR remediation methodology

The prior Phase 8B-2 number used one path's Sharpe sampling standard error as
both the uncertainty of that observed path and the dispersion of the historical
trial Sharpe distribution. Those are different quantities, so that construction
is not labelled Bailey–López de Prado DSR in this remediation.

For a genuinely comparable vector of historical economic trial Sharpes
\(S_1,\ldots,S_N\), define

\[
\bar S_{trial}=N^{-1}\sum_i S_i,\qquad
\sigma_{trial}^2=(N-1)^{-1}\sum_i(S_i-\bar S_{trial})^2.
\]

With \(N_{eff}\) independent/effective trials, the published expected-maximum
normal approximation is

\[
z_{max}(N_{eff})=(1-\gamma)\Phi^{-1}(1-1/N_{eff})
 +\gamma\Phi^{-1}(1-1/(eN_{eff})),
\]

where \(\gamma=0.5772156649\) is Euler's constant. In this audit's explicit
trial-distribution formulation,

\[
SR^*=\bar S_{trial}+\sigma_{trial}z_{max}(N_{eff}).
\]

The observed OOS path has its own sampling uncertainty. For observed Sharpe
\(SR_{observed}\), sample length \(T\), skewness \(g_1\), and excess kurtosis
\(g_2\), the Bailey–López de Prado sampling approximation is

\[
\sigma_{observed}^2=
\frac{1-g_1SR_{observed}+((g_2+2)/4)SR_{observed}^2}{T-1}.
\]

The DSR test statistic and probability are

\[
z_{DSR}=\frac{SR_{observed}-SR^*}{\sigma_{observed}},
\qquad DSR=\Phi(z_{DSR}).
\]

Thus \(\bar S_{trial}\) and \(\sigma_{trial}\) describe cross-trial
dispersion, while \(\sigma_{observed}\) describes sampling uncertainty of the
one observed path. The raw research counts (2,800 strict and 4,164
conservative) are governance counts; they cannot replace the number of actual
comparable Sharpe observations. Correlation/effective-trial estimates are
sensitivity diagnostics only.

The canonical Phase 1–7 artifacts do not provide a single accepted Sharpe
distribution with the same 2013-01-02 through 2026-08-31 OOS calendar for all
historical trials. Phase 1–6 and Phase 7A full-sample rows use the 2006–2026
full sample; Phase 7B candidate Sharpes use changing expanding training folds;
only the small final OOS path family has the common OOS calendar and it is the
already frozen White Reality Check family, not the complete research history.
Mixing these populations would make \(\sigma_{trial}\) non-identifiable and
would manufacture a DSR. The corrected result is therefore
`DSR_NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACTS`.
