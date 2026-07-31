# Atlas ROS v8.3.0 Authority Activation

This transaction activates the published Atlas ROS v8.3.0 software release only.
It does not deploy or enable the production event runtime, Todoist or Notion
webhooks, background workers, or autonomous provider writes.

## Immutable release identity

- Tag: `v8.3.0`
- Publication commit: `88ce7fecabdb20c62410e8af151653ec5e7dd511`
- Package source commit: `ac546f10ee4c1e140d17beaae32f7ea77eb12a51`
- Manifest SHA-256: `e9ec73a996e57224d39122f717c86fa53f62005ede88125664339b88651eb972`
- Source SHA-256: `d180ac3367229b6bdf5ca160acb5221e8800807909bef85b30aa3615347fafbf`
- Wheel SHA-256: `d76a43aa99e629fe8055920f325028a2b64eefa6f10e1d0497419805b622f5fe`

## Independent publication evidence

- Audit workflow run: `30657117807`
- Audit artifact: `8803677584`
- Artifact SHA-256: `10fab327ac4ae997464db00a94f0b6530e8b23e230630bbfd1d170be43fbbbd5`
- Audit receipt SHA-256: `28e9f8dd48062a7aa529ad7f82c41224c717830abb23a70b620c13873a3c0653`
- Result: all 11 release assets verified; clean source and wheel installs passed;
  v8.2.1 and v8.2.0 restoration checks passed; package rebuilt false;
  provider, Notion, and Todoist writes zero.

## Authority transition

- Active release: v8.3.0 at the immutable publication commit above.
- Immediate rollback: v8.2.1 at `38285a988ef0e265ad859474c3bdcb58a1744649`.
- First historical rollback: v8.2.0 at `64c38eb4e83f6edf2d6cff28f7c7556a2c84c0c9`.
- Release Index SHA-256: `b9b58f42fe1675204ed958371e93c5a3f965ad6a6eb7e834f05905e087713c11`.
- Authority integrity SHA-256: `20dfd7883f6c8346dcc5e24cc5793636789cdab8a9b346e604e38dfb611f6494`.

Automation V4M-6 remains `validated_not_active` at A0 Observe. The default
autonomy mode remains monitor-only, the kill switch remains engaged, and ingress
remains disabled. Runtime activation requires its own infrastructure,
monitor-only acceptance evidence, and exact policy-activation authorization.
