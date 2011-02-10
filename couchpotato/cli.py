from couchpotato import app
import argparse

def cmd_couchpotato():
    """Commandline entry point."""
    # Make sure views are imported and registered.
    import couchpotato.views
    app.run(debug=True)
