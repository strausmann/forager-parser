# Makefile für forager-parser

.PHONY: help test test-samples parse-rewe parse-lidl parse-dm

help:
	@echo "Verfügbare Befehle:"
	@echo "  make test         - Führt pytest und alle Samples aus"
	@echo "  make test-samples - Parst alle Sample-Bons unter merchants/"
	@echo "  make parse-rewe   - Testet das Parsing für REWE-Belege (Sample)"
	@echo "  make parse-lidl   - Testet das Parsing für Lidl-Belege (Sample)"
	@echo "  make parse-dm     - Testet das Parsing für dm-Belege (Sample)"

# Alle Tests ausführen

test:
	pytest src/forager_parser -v
	$(MAKE) test-samples

test-samples:
	@set -e; \
	for sample in $$(find merchants -path '*/samples/*.txt' -type f | sort); do \
		echo "[sample] $$sample"; \
		python -m forager_parser.cli parse "$$sample" --profiles-dir merchants >/dev/null; \
	done

# Beispiel: REWE-Beleg parsen

parse-rewe:
	python -m forager_parser.cli parse merchants/de/rewe/samples/2026-03-21-hamburg-ueberseequartier.txt

# Beispiel: Lidl-Beleg parsen

parse-lidl:
	python -m forager_parser.cli parse merchants/de/lidl/samples/2026-05-19-seevetal.txt

# Beispiel: dm-Beleg parsen

parse-dm:
	python -m forager_parser.cli parse merchants/de/dm/samples/2025-01-25-hamburg-fischbek.txt
