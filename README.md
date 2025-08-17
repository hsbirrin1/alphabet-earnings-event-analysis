# alphabet-earnings-event-analysis

This project analyzes market reactions to Alphabet’s (GOOGL) annual 10-K filings using an event study approach. It combines stock price data from Yahoo Finance with fundamentals from SEC EDGAR to explore how investors respond to annual disclosures.

Overview
The goal of this project is to examine whether Alphabet’s 10-K filings trigger abnormal stock returns in the short and medium term. The study also evaluates how financial ratios (liquidity, leverage, profitability) correlate with market performance after these events.

Key questions:
Do GOOGL shares typically rise or fall after a 10-K release?
Are the effects short-lived or persistent?
How do fundamentals like ROE, ROA, and debt-to-equity align with post-event stock performance?

Methodology
Data Sources
Yahoo Finance → Daily stock prices (GOOGL and S&P 500 benchmark)
SEC EDGAR → Filing dates and financial statement data (10-K)

Event Study Setup
Event date = first trading day after each 10-K filing
Windows analyzed: 5-day, 20-day, 30-day forward returns
Pre-event vs. post-event returns compared using a t-test

Fundamentals
Financial ratios extracted from EDGAR (10-Ks only):
Current Ratio
Quick Ratio
Debt-to-Equity
Return on Equity (ROE)
Return on Assets (ROA)

Analysis Steps
Fetch stock + filing data
Align events to next trading day
Compute forward returns (5d, 20d, 30d)
Run t-tests on pre- vs. post-event returns
Correlate financial ratios with post-event returns
Plot stock prices around filing dates

Results
5-Day Window: Consistent short-term dips, statistically significant at the 5% level.
20-Day Window: Slightly negative, not statistically significant.
30-Day Window: Flat to marginally negative, impact fades.
Latest 10-K (2025): Stock dropped ~7% within days of filing (significant), mainly due to:
Slower Google Cloud growth 
$75B capital expenditure plan vs. ~$60B expected
Market reaction shows a “buy the rumor, sell the news” effect.
Long-term fundamentals remain strong; investors tend to buy the dip.

Built 
Building a mini data pipeline and running statistical models.
In this project, the pipeline looks like this:

Data Ingestion
Pulled daily stock prices from Yahoo Finance
Pulled 10-K filing dates and financials from SEC EDGAR

Processing / Transformation
Mapped filing dates to the next trading day
Calculated forward returns (5d, 20d, 30d)
Computed financial ratios (ROE, ROA, current ratio, etc.)

Integration
Combined stock data + financial ratios into a single dataset
Flagged the event date (K10_filed = 1)

Output
Ran t-tests on returns before vs. after events
Correlation analysis between ratios & returns
Generated plots of stock prices around filings

Statistical Models Part
t-tests → test if pre-event vs. post-event returns differ significantly
Correlation matrix → see relationships between fundamentals (ROE, ROA, debt/equity) and returns
Event study framework itself is a classic applied econometric/statistical model in finance
