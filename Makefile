.PHONY: app clean install-deps run

# Build macOS app bundle
app:
	@echo "Building macOS app bundle..."
	python setup.py py2app
	@echo "App built successfully! Find it in dist/Obsidian Clone.app"
	@echo "To install: drag dist/Obsidian Clone.app to your Applications folder"

# Clean build artifacts
clean:
	rm -rf build dist *.egg-info
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

# Install dependencies including py2app
install-deps:
	pip install -r requirements.txt
	pip install py2app

# Run the app directly (for development)
run:
	python obsidian_clone.py

# Build and install to Applications folder (requires admin password)
install: app
	@echo "Installing to /Applications..."
	cp -R "dist/Obsidian Clone.app" /Applications/
	@echo "Obsidian Clone installed to Applications!"