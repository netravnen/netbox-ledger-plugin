"""Re-derive frozen exchange rates from the current Currency.base_rate values.

Opt-in, and deliberately not run by the 0003 migration. Expenses created before
the conversion bug was fixed may carry a rate of 1 because the old bulk import
path stored an unconverted `amount_native`; this command repairs those rows. It
will also re-price expenses whose rate was correct at the time but differs from
today's rate, which is usually *not* what you want -- so it defaults to a dry run
and is scoped to one ledger at a time.
"""

from django.core.management.base import BaseCommand, CommandError

from ...calc.currency import rate_between
from ...models import Expense, Ledger


class Command(BaseCommand):
    help = 'Re-derive Expense.fx_rate from current exchange rates for one ledger (dry run by default)'

    def add_arguments(self, parser):
        parser.add_argument('ledger', help='Name or numeric ID of the ledger to recompute')
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Write the recomputed rates. Without this the command only reports what would change.',
        )
        parser.add_argument(
            '--only-unconverted',
            action='store_true',
            help='Limit to expenses whose stored rate is exactly 1 but whose currency differs from the '
            "ledger's, i.e. the rows the old bulk import path corrupted.",
        )

    def handle(self, *args, **options):
        ledger = self._get_ledger(options['ledger'])
        apply_changes = options['apply']
        only_unconverted = options['only_unconverted']

        expenses = Expense.objects.filter(ledger=ledger).select_related('currency', 'ledger__currency')
        changed = skipped = 0

        for expense in expenses:
            current = expense.fx_rate
            correct = rate_between(expense.currency, ledger.currency)

            if only_unconverted and not (current == 1 and expense.currency_id != ledger.currency_id):
                skipped += 1
                continue
            if current == correct:
                skipped += 1
                continue

            self.stdout.write(
                f'{"Updating" if apply_changes else "Would update"} #{expense.pk} {expense.name!r}: '
                f'{current} -> {correct} ({expense.amount} {expense.currency} = '
                f'{expense.amount * correct:.2f} {ledger.currency})'
            )
            if apply_changes:
                expense.fx_rate = correct
                # save() recomputes amount_native from the new rate; the parts are
                # restated too so a part can never disagree with its expense.
                expense.save()
                for part in expense.parts.all():
                    part.save()
            changed += 1

        verb = 'Updated' if apply_changes else 'Would update'
        self.stdout.write(self.style.SUCCESS(f'{verb} {changed} expense(s); {skipped} already correct or skipped.'))
        if changed and not apply_changes:
            self.stdout.write('Re-run with --apply to write these changes.')

    def _get_ledger(self, reference):
        if reference.isdigit():
            ledger = Ledger.objects.filter(pk=int(reference)).first()
        else:
            ledger = Ledger.objects.filter(name=reference).first()
        if ledger is None:
            raise CommandError(f'No ledger matching {reference!r}')
        return ledger
