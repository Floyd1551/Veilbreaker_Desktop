from veilbreaker.map_smoke import smoke
import sys
raise SystemExit(smoke(sys.argv[1] if len(sys.argv)>1 else 'test-artifacts/map-source', sys.argv[2] if len(sys.argv)>2 else None))
