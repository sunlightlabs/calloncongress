import os
from calloncongress import app, settings
app.run(debug=settings.DEBUG, port=int(os.environ.get('PORT', 5000)))
