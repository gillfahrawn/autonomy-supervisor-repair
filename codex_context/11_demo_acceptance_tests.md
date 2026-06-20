The demo is successful if:

1. It runs locally with one command:
   make demo

2. It generates at least 100 synthetic scenario runs.

3. The baseline supervisor fails at least one property.

4. The system generates at least 5 candidate patches.

5. At least one candidate improves the total violation score by 30%+.

6. The system writes a human-readable report.

7. The code has unit tests for:
   - state-machine parsing
   - transition evaluation
   - trace generation
   - property checking
   - patch generation
   - scoring