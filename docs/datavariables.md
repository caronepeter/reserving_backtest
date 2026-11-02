| Column | Meaning | Schedule P Part | Units | Used? |
|:-------|---------|-----------------|-------|-------|
| GRCODE | Company Code | None (identifier) | NA | Yes |
| GRNAME | Company Name | None (identifier) | NA | Yes |
| AccidentYear | Accident Year | The row of every triangle | Year | Yes |
| DevelopmentYear | Development Year | the column | Year | Yes |
| DevelopmentLag | DevelopmentYear - AccidentYear + 1 | None (derived) | Year | Yes |
| IncurredLosses | Incurred losses and allocated expenses at year end, includes bulk and IBNR reserves, net of reinsurance | 2 | $000 | Yes, used with BulkLoss to calculate reported claims |
| CumPaidLoss | Cumulative paid losses and allocated expenses at year end, net of reinsurance | 3 | $000 | Yes, paid claims|
| BulkLoss | Bulk and IBNR reserves at year end, net of reinsurance | 4 | $000 | Yes, used with IncurredLosses to calculate reported claims |
| EarnedPremDIR | Premiums earned at incurral year - direct and assumed | 1 | $000 | Cleaning check only |
| EarnedPremCeded | Premiums earned at incurral year - ceded | 1 | $000 | Cleaning check only |
| EarnedPremNet | Premiums earned at incurral year - net of reinsurance | 1 | $000 | Yes, earned premium |
| Single | Single entity (1) or group insurer (0) | None | 1/0 | Yes |
| PostedReserves2007 | Posted unpaid loss and LAE reserves at 12/31/2007, all AYs including pre-1998 | None (U&I Exhibit Part 2A) | $000 | No |