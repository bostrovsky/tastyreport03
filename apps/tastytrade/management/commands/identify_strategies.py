"""
Management command to identify trading strategies from existing transactions
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.tastytrade.strategy_identifier import run_strategy_identification

User = get_user_model()


class Command(BaseCommand):
    help = 'Identify trading strategies from existing transactions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Username to process (default: all users)',
        )
        parser.add_argument(
            '--account',
            type=str,
            help='Account number to process (default: all accounts)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be identified without creating strategies',
        )

    def handle(self, *args, **options):
        users = User.objects.all()
        
        if options['user']:
            users = users.filter(username=options['user'])
            if not users.exists():
                self.stdout.write(
                    self.style.ERROR(f'User "{options["user"]}" not found')
                )
                return

        total_strategies = 0
        
        for user in users:
            self.stdout.write(f'\nProcessing user: {user.username}')
            
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING('DRY RUN MODE - No strategies will be created')
                )
            
            try:
                strategies = run_strategy_identification(
                    user, 
                    account_number=options['account']
                )
                
                if strategies:
                    total_strategies += len(strategies)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  Created {len(strategies)} strategies'
                        )
                    )
                    
                    for strategy in strategies:
                        self.stdout.write(
                            f'    - {strategy.get_strategy_type_display()}: '
                            f'{strategy.underlying_symbol} '
                            f'(confidence: {strategy.confidence_score}%)'
                        )
                else:
                    self.stdout.write('  No new strategies identified')
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  Error processing user {user.username}: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted! Total strategies created: {total_strategies}'
            )
        )