import json
from activity_logs.models import ActivityLog
from django.db import models

res = {
    'distinct_actions': list(ActivityLog.objects.all().values('action_type', 'entity_name').distinct()),
    'counts': list(ActivityLog.objects.values('action_type').annotate(count=models.Count('id'))),
    'latest': [str(l) for l in ActivityLog.objects.all()[:5]]
}

with open('log_summary.json', 'w') as f:
    json.dump(res, f, indent=2)
