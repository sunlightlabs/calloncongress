#!/usr/bin/env python
import os
from calloncongress import app, settings
app.run(debug=settings.DEBUG, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
