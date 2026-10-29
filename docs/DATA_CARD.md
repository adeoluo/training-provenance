# Data Card - Training Provenance

## Sources and provenance
The data is a **generated** linear-regression dataset produced by `make_dataset` in
`src/training_provenance/pipeline.py`. A hidden weight vector and bias define a linear function;
feature rows are sampled uniformly and labels are that function plus small Gaussian noise. The
dataset exists to exercise the provenance machinery end to end; it is not the contribution.

## Licensing
The generator and the demonstration transforms are original to this project under the
repository's MIT license. No external corpus is used.

## Composition
A dataset is a mapping with `features` (a list of numeric rows) and `labels` (a list of numbers).
The default is 200 rows and 4 features. Configurations are small mappings such as the ridge
penalty. Checkpoints are the fitted weights and bias. Metrics are mean squared error and the
coefficient of determination.

## Preprocessing and filtering
The tracked `standardize` transform z-scores the features deterministically. No personally
identifiable information is present and there is no free text.

## Contamination checks
Not applicable in the usual sense: there is a single dataset per run and evaluation is in-sample,
because the goal is to demonstrate reproducible tracking rather than generalization. The metrics
are reproducible, which is the property under test.

## Known biases and gaps
The dataset is linear by construction and small. The transforms are simple and deterministic on
purpose, since nondeterministic steps cannot be verified by re-execution without first pinning
their randomness.

## Ethical considerations
The data is synthetic and contains no personal or sensitive content. The system's purpose,
reproducibility and integrity, is itself a responsible-AI control.
