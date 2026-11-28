
# PathImpact Decision-Support Rules

## Rule Version

Version: 1.0.0

## Purpose

PathImpact uses student self-assessment ratings and predefined
academic relationships to provide advisory information about
competency gaps and preparation for succeeding subjects.

These rules are developer-defined and are not scientifically
validated measurements of academic ability.

## 1. Self-Assessment Scale

| Rating | Interpretation |
|---|---|
| 1 | Needs significant strengthening |
| 2 | Needs strengthening |
| 3 | Further practice recommended |
| 4 | Self-reported independent ability |
| 5 | Self-reported ability to explain |

Ratings 1 through 3 are treated as identified competency gaps
for review planning.

Ratings 4 and 5 do not generate review recommendations.

## 2. Competency Relevance

| Relevance | Weight |
|---|---|
| Low | 1 |
| Medium | 2 |
| High | 3 |

Relevance describes the defined importance of a prerequisite
competency to a succeeding subject.

## 3. Readiness Calculation

Weighted readiness is calculated as:

R = sum(rating * relevance weight) / sum(relevance weight)

Classification uses the unrounded calculated score.

| Score | Readiness Level |
|---|---|
| 1.00 to below 3.00 | Needs strengthening |
| 3.00 to below 4.00 | Developing readiness |
| 4.00 to 5.00 | Higher readiness |

Displayed scores are rounded to two decimal places.

Missing required ratings result in insufficient information.

Subjects without defined competency impacts do not receive
a readiness classification.

## 4. Impact Analysis

A succeeding subject is considered potentially affected
when at least one explicitly linked prerequisite competency
has a self-rating from 1 to 3.

Prerequisite relationships alone do not establish
competency impacts.

## 5. Review Priority

Priority score = (5 - self-rating) * relevance weight

Only identified competency gaps generate recommendations.

Recommendations are sorted by:

1. Highest priority score
2. Highest relevance
3. Lowest self-rating
4. Competency code
5. Succeeding subject code
6. Stable record identifiers

Rank 1 represents the highest review priority.

## 6. Missing Information

Missing ratings are not assigned a value of zero.

An incomplete assessment does not produce readiness results.

A completed assessment without responses does not produce
readiness results.

Missing competency impact relationships are not invented.

## 7. Privacy and Ownership

Individual analysis is restricted to the active student
who owns the assessment.

Administrators cannot access another student's individual
analysis through the analysis service.

## 8. Limitations

PathImpact does not:

- Predict grades or academic performance.
- Guarantee academic success.
- Establish objective competency mastery.
- Determine enrollment eligibility.
- Modify official academic records.
- Replace academic advisers or professors.

## 9. Implementation Status

Version 1.0.0 initially provides read-only calculation
services using the current academic reference catalog.

Persistent readiness results, recommendation storage,
historical snapshots, and student interface integration
are separate implementation milestones.
