from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Count


class Command(BaseCommand):
    help = 'Find and remove duplicate users by username'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Actually delete the duplicate users (without this flag, just shows what would be deleted)',
        )

    def handle(self, *args, **options):
        # Find usernames with duplicates
        duplicates = User.objects.values('username').annotate(
            count=Count('id')
        ).filter(count__gt=1)

        if not duplicates:
            self.stdout.write(self.style.SUCCESS('No duplicate users found.'))
            return

        self.stdout.write(self.style.WARNING(f'Found {duplicates.count()} duplicate username(s):'))
        
        for dup in duplicates:
            username = dup['username']
            users = User.objects.filter(username=username).order_by('date_joined')
            
            self.stdout.write(f'\nUsername: {username}')
            for user in users:
                self.stdout.write(
                    f'  - ID: {user.id}, Email: {user.email}, '
                    f'Created: {user.date_joined}, Active: {user.is_active}, '
                    f'Staff: {user.is_staff}'
                )
            
            # Keep the first one, mark others for deletion
            to_delete = users[1:]
            
            if options['fix']:
                self.stdout.write(self.style.WARNING(f'  Deleting {len(to_delete)} duplicate(s)...'))
                for user in to_delete:
                    user.delete()
                self.stdout.write(self.style.SUCCESS(f'  ✓ Deleted {len(to_delete)} duplicate user(s)'))
            else:
                self.stdout.write(
                    f'  Would delete {len(to_delete)} duplicate(s). Use --fix to actually delete.'
                )

        self.stdout.write(self.style.SUCCESS('\nDuplicate cleanup complete!'))
