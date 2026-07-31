from collections import OrderedDict
from decimal import ROUND_DOWN, Decimal

import networkx as nx
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View
from netbox.object_actions import CloneObject, DeleteObject, EditObject
from netbox.plugins import get_plugin_config
from netbox.ui.layout import SimpleLayout
from netbox.ui.panels import ObjectsTablePanel, TemplatePanel
from netbox.views.generic import (
    BulkDeleteView,
    BulkEditView,
    BulkImportView,
    ObjectDeleteView,
    ObjectEditView,
    ObjectListView,
    ObjectView,
)
from utilities.views import ContentTypePermissionRequiredMixin, GetReturnURLMixin, register_model_view

from .calc.basic import basic_calc
from .calc.currency import result_to_decimal
from .calc.matrix import result_to_matrix
from .calc.mincost import solve_mincost_problem_for_expenses
from .calc.minpayments import solve_min_payments_for_expenses
from .choices import LedgerCalcMethodChoices
from .filtersets import (
    CurrencyFilterSet,
    ExpenseFilterSet,
    ExpensePartFilterSet,
    LedgerFilterSet,
    PersonFilterSet,
    SettlementFilterSet,
)
from .forms import (
    CurrencyBulkEditForm,
    CurrencyFilterForm,
    CurrencyForm,
    CurrencyImportForm,
    ExpenseBulkEditForm,
    ExpenseFilterForm,
    ExpenseForm,
    ExpenseImportForm,
    ExpensePartBulkEditForm,
    ExpensePartFilterForm,
    ExpensePartForm,
    ExpenseSplitForm,
    LedgerBulkEditForm,
    LedgerFilterForm,
    LedgerForm,
    LedgerImportForm,
    LedgerPickerForm,
    PersonBulkEditForm,
    PersonFilterForm,
    PersonForm,
    PersonImportForm,
    SettlementBulkEditForm,
    SettlementFilterForm,
    SettlementForm,
    SettlementImportForm,
)
from .models import Currency, Expense, ExpensePart, Ledger, Person, Settlement
from .summary import build_ledger_calc_inputs, ledger_person_balances
from .tables import (
    CurrencyTable,
    ExpensePartTable,
    ExpenseTable,
    LedgerTable,
    PersonTable,
    SettlementTable,
)
from .ui.panels import (
    CurrencyPanel,
    ExpensePanel,
    ExpensePartPanel,
    LedgerPanel,
    PersonPanel,
    SettlementPanel,
)

###
# Currency
###


@register_model_view(Currency)
class CurrencyView(ObjectView):
    actions = (CloneObject, EditObject, DeleteObject)
    queryset = Currency.objects.all()
    template_name = 'netbox_ledger_tracker/currency.html'
    layout = SimpleLayout(
        left_panels=[CurrencyPanel()],
        right_panels=[TemplatePanel('inc/panels/tags.html')],
    )


@register_model_view(Currency, name='list', path='', detail=False)
class CurrencyListView(ObjectListView):
    queryset = Currency.objects.all()
    table = CurrencyTable
    filterset = CurrencyFilterSet
    filterset_form = CurrencyFilterForm


@register_model_view(Currency, name='add', detail=False)
@register_model_view(Currency, name='edit')
class CurrencyEditView(ObjectEditView):
    queryset = Currency.objects.all()
    form = CurrencyForm


@register_model_view(Currency, name='delete')
class CurrencyDeleteView(ObjectDeleteView):
    queryset = Currency.objects.all()


@register_model_view(Currency, name='bulk_import', path='import', detail=False)
class CurrencyBulkImportView(BulkImportView):
    queryset = Currency.objects.all()
    model_form = CurrencyImportForm


@register_model_view(Currency, name='bulk_edit', path='edit', detail=False)
class CurrencyBulkEditView(BulkEditView):
    queryset = Currency.objects.all()
    table = CurrencyTable
    form = CurrencyBulkEditForm


@register_model_view(Currency, name='bulk_delete', path='delete', detail=False)
class CurrencyBulkDeleteView(BulkDeleteView):
    queryset = Currency.objects.all()
    table = CurrencyTable


###
# Ledger
###


@register_model_view(Ledger)
class LedgerView(ObjectView):
    actions = (CloneObject, EditObject, DeleteObject)
    queryset = Ledger.objects.select_related('currency').prefetch_related('tags')
    template_name = 'netbox_ledger_tracker/ledger.html'
    layout = SimpleLayout(
        left_panels=[LedgerPanel()],
        right_panels=[TemplatePanel('inc/panels/tags.html')],
        bottom_panels=[
            ObjectsTablePanel(
                model='netbox_ledger_tracker.person',
                title='People',
                filters={'ledger_id': lambda ctx: ctx['object'].pk},
                exclude_columns=['ledger'],
            ),
            ObjectsTablePanel(
                model='netbox_ledger_tracker.expense',
                title='Expenses',
                filters={'ledger_id': lambda ctx: ctx['object'].pk},
                exclude_columns=['ledger'],
            ),
            ObjectsTablePanel(
                model='netbox_ledger_tracker.settlement',
                title='Settlements',
                filters={'ledger_id': lambda ctx: ctx['object'].pk},
                exclude_columns=['ledger'],
            ),
        ],
    )

    def get_extra_context(self, request, instance):
        return {
            'can_add_expense': request.user.has_perm('netbox_ledger_tracker.add_expense'),
            'can_add_settlement': request.user.has_perm('netbox_ledger_tracker.add_settlement'),
            'balances': ledger_person_balances(instance),
        }


@register_model_view(Ledger, name='list', path='', detail=False)
class LedgerListView(ObjectListView):
    queryset = Ledger.objects.select_related('currency')
    table = LedgerTable
    filterset = LedgerFilterSet
    filterset_form = LedgerFilterForm


@register_model_view(Ledger, name='add', detail=False)
@register_model_view(Ledger, name='edit')
class LedgerEditView(ObjectEditView):
    queryset = Ledger.objects.all()
    form = LedgerForm


@register_model_view(Ledger, name='delete')
class LedgerDeleteView(ObjectDeleteView):
    queryset = Ledger.objects.all()


@register_model_view(Ledger, name='bulk_import', path='import', detail=False)
class LedgerBulkImportView(BulkImportView):
    queryset = Ledger.objects.all()
    model_form = LedgerImportForm


@register_model_view(Ledger, name='bulk_edit', path='edit', detail=False)
class LedgerBulkEditView(BulkEditView):
    queryset = Ledger.objects.all()
    table = LedgerTable
    form = LedgerBulkEditForm


@register_model_view(Ledger, name='bulk_delete', path='delete', detail=False)
class LedgerBulkDeleteView(BulkDeleteView):
    queryset = Ledger.objects.all()
    table = LedgerTable


@register_model_view(Ledger, name='settle_up', path='settle-up')
class LedgerSettleUpView(ContentTypePermissionRequiredMixin, View):
    """Compute and display the debt matrix for a Ledger using its configured calc_method."""

    queryset = Ledger.objects.all()

    def get_required_permission(self):
        return 'netbox_ledger_tracker.view_ledger'

    def get(self, request, pk):
        ledger = get_object_or_404(Ledger.objects.select_related('currency'), pk=pk)
        people = list(Person.objects.filter(ledger=ledger))
        people_by_id = OrderedDict((person.pk, person.name) for person in people)

        # Money already handed over reduces what is still outstanding, so the
        # matrix shows what remains rather than the original debt. Built by the
        # same helper the balance table uses, so the two cannot disagree.
        calc_data, settlement_data, inconsistent_expense_ids = build_ledger_calc_inputs(ledger)

        balances = ledger_person_balances(ledger, people)
        max_exact_people = get_plugin_config('netbox_ledger_tracker', 'minimal_max_people', 12)
        # The exact partition is exponential, so say so rather than silently
        # handing back a different algorithm's answer.
        minimal_fell_back = ledger.calc_method == LedgerCalcMethodChoices.MINIMAL and (
            sum(1 for row in balances if row['net'] != 0) > max_exact_people
        )

        matrix = None
        error = None
        if calc_data and people_by_id:
            person_ids = list(people_by_id)
            try:
                if ledger.calc_method == LedgerCalcMethodChoices.MINIMAL:
                    fraction_result = solve_min_payments_for_expenses(
                        calc_data,
                        person_ids,
                        settlements=settlement_data,
                        max_exact_people=max_exact_people,
                    )
                elif ledger.calc_method == LedgerCalcMethodChoices.OPTIMIZED:
                    fraction_result = solve_mincost_problem_for_expenses(
                        calc_data, person_ids, settlements=settlement_data
                    )
                else:
                    fraction_result = basic_calc(calc_data, person_ids, settlements=settlement_data)
            except nx.NetworkXUnfeasible:
                error = (
                    'Could not calculate an optimized settlement because the expense data is inconsistent. '
                    'Switch this ledger to the basic calculation method, or fix the flagged expenses below.'
                )
            else:
                matrix = result_to_matrix(result_to_decimal(fraction_result), people_by_id)

        return render(
            request,
            'netbox_ledger_tracker/ledger_settle_up.html',
            {
                'object': ledger,
                'ledger': ledger,
                'people': people,
                'matrix': matrix,
                'error': error,
                'inconsistent_expense_ids': inconsistent_expense_ids,
                'settlement_count': len(settlement_data),
                'balances': balances,
                'minimal_fell_back': minimal_fell_back,
                'minimal_max_people': max_exact_people,
            },
        )


###
# Person
###


@register_model_view(Person)
class PersonView(ObjectView):
    actions = (CloneObject, EditObject, DeleteObject)
    queryset = Person.objects.select_related('ledger', 'user').prefetch_related('tags')
    template_name = 'netbox_ledger_tracker/person.html'
    layout = SimpleLayout(
        left_panels=[PersonPanel()],
        right_panels=[TemplatePanel('inc/panels/tags.html')],
    )


@register_model_view(Person, name='list', path='', detail=False)
class PersonListView(ObjectListView):
    queryset = Person.objects.select_related('ledger', 'user')
    table = PersonTable
    filterset = PersonFilterSet
    filterset_form = PersonFilterForm


@register_model_view(Person, name='add', detail=False)
@register_model_view(Person, name='edit')
class PersonEditView(ObjectEditView):
    queryset = Person.objects.all()
    form = PersonForm


@register_model_view(Person, name='delete')
class PersonDeleteView(ObjectDeleteView):
    queryset = Person.objects.all()


@register_model_view(Person, name='bulk_import', path='import', detail=False)
class PersonBulkImportView(BulkImportView):
    queryset = Person.objects.all()
    model_form = PersonImportForm


@register_model_view(Person, name='bulk_edit', path='edit', detail=False)
class PersonBulkEditView(BulkEditView):
    queryset = Person.objects.all()
    table = PersonTable
    form = PersonBulkEditForm


@register_model_view(Person, name='bulk_delete', path='delete', detail=False)
class PersonBulkDeleteView(BulkDeleteView):
    queryset = Person.objects.all()
    table = PersonTable


###
# Expense
###


@register_model_view(Expense)
class ExpenseView(ObjectView):
    actions = (CloneObject, EditObject, DeleteObject)
    queryset = Expense.objects.select_related('ledger', 'currency').prefetch_related('tags')
    template_name = 'netbox_ledger_tracker/expense.html'
    layout = SimpleLayout(
        left_panels=[ExpensePanel()],
        right_panels=[TemplatePanel('inc/panels/tags.html')],
        bottom_panels=[
            ObjectsTablePanel(
                model='netbox_ledger_tracker.expensepart',
                title='Split',
                filters={'expense_id': lambda ctx: ctx['object'].pk},
                exclude_columns=['expense'],
            ),
        ],
    )

    def get_extra_context(self, request, instance):
        return {
            'can_change_expense': request.user.has_perm('netbox_ledger_tracker.change_expense'),
        }


@register_model_view(Expense, name='list', path='', detail=False)
class ExpenseListView(ObjectListView):
    queryset = Expense.objects.select_related('ledger', 'currency')
    table = ExpenseTable
    filterset = ExpenseFilterSet
    filterset_form = ExpenseFilterForm


@register_model_view(Expense, name='edit')
class ExpenseEditView(ObjectEditView):
    """Header-only quick edit. Use Split Expense to change the per-person breakdown."""

    queryset = Expense.objects.all()
    form = ExpenseForm


@register_model_view(Expense, name='delete')
class ExpenseDeleteView(ObjectDeleteView):
    queryset = Expense.objects.all()


@register_model_view(Expense, name='bulk_import', path='import', detail=False)
class ExpenseBulkImportView(BulkImportView):
    queryset = Expense.objects.all()
    model_form = ExpenseImportForm


@register_model_view(Expense, name='bulk_edit', path='edit', detail=False)
class ExpenseBulkEditView(BulkEditView):
    queryset = Expense.objects.all()
    table = ExpenseTable
    form = ExpenseBulkEditForm


@register_model_view(Expense, name='bulk_delete', path='delete', detail=False)
class ExpenseBulkDeleteView(BulkDeleteView):
    queryset = Expense.objects.all()
    table = ExpenseTable


class ExpenseSplitView(ContentTypePermissionRequiredMixin, GetReturnURLMixin, View):
    """Create or replace an Expense's full per-person breakdown in one screen.

    Handles both "add" (no pk) and "edit" (pk supplied) — mirrors the
    original buddyledger AddExpense/EditExpense views, which always showed
    every ledger member as a row (involved checkbox + paid/owed fields) on
    a single screen rather than a separate "who's involved" step.

    Since the per-person fields depend on which ledger's members to show,
    and that isn't known until a ledger is chosen, this is a two-step flow
    when no ledger is given yet: a small GET-submitted :class:`LedgerPickerForm`
    picks the ledger (reloading this same view with ``?ledger=<pk>``), then
    the full :class:`ExpenseSplitForm` is rendered for that ledger's people.
    """

    queryset = Expense.objects.all()
    default_return_url = 'plugins:netbox_ledger_tracker:expense_list'

    def get_required_permission(self):
        return 'netbox_ledger_tracker.change_expense' if self.kwargs.get('pk') else 'netbox_ledger_tracker.add_expense'

    def _get_expense(self):
        pk = self.kwargs.get('pk')
        if pk is None:
            return None
        return get_object_or_404(Expense.objects.select_related('ledger', 'currency'), pk=pk)

    def get(self, request, pk=None):
        expense = self._get_expense()
        ledger = expense.ledger if expense else None

        if ledger is None:
            ledger_id = request.GET.get('ledger')
            if ledger_id:
                ledger = get_object_or_404(Ledger, pk=ledger_id)

        if ledger is None:
            return render(
                request,
                'netbox_ledger_tracker/expense_split_pick_ledger.html',
                {'form': LedgerPickerForm(), 'return_url': self.get_return_url(request)},
            )

        initial = {'currency': ledger.currency_id, 'ledger': ledger.pk}
        existing_parts = {}
        if expense:
            initial.update(
                {
                    'name': expense.name,
                    'currency': expense.currency_id,
                    'amount': expense.amount,
                    'date': expense.date,
                    'comments': expense.comments,
                }
            )
            existing_parts = {part.person_id: part for part in expense.parts.select_related('person')}

        people = list(Person.objects.filter(ledger=ledger))
        form = ExpenseSplitForm(initial=initial)
        form.add_person_fields(people, existing_parts)

        return render(
            request,
            'netbox_ledger_tracker/expense_split.html',
            {
                'form': form,
                'expense': expense,
                'ledger': ledger,
                'return_url': self.get_return_url(request, expense),
            },
        )

    def post(self, request, pk=None):
        expense = self._get_expense()

        # Learn which ledger was submitted so we know whose per-person fields to attach,
        # then build the real, fully-fielded form against that ledger's people.
        precheck_form = ExpenseSplitForm(data=request.POST, expense=expense)
        ledger = None
        if precheck_form.is_valid():
            ledger = precheck_form.cleaned_data['ledger']
        elif precheck_form.data.get('ledger'):
            ledger = Ledger.objects.filter(pk=precheck_form.data['ledger']).first()

        people = list(Person.objects.filter(ledger=ledger)) if ledger else []

        form = ExpenseSplitForm(data=request.POST, expense=expense)
        form.add_person_fields(people)

        if not form.is_valid():
            return render(
                request,
                'netbox_ledger_tracker/expense_split.html',
                {
                    'form': form,
                    'expense': expense,
                    'ledger': ledger,
                    'return_url': self.get_return_url(request, expense),
                },
            )

        ledger = form.cleaned_data['ledger']
        currency = form.cleaned_data['currency']
        amount = form.cleaned_data['amount']
        involved_people = form.get_involved_people(people)

        if not involved_people:
            form.add_error(None, 'Select at least one person as involved in this expense.')
            return render(
                request,
                'netbox_ledger_tracker/expense_split.html',
                {
                    'form': form,
                    'expense': expense,
                    'ledger': ledger,
                    'return_url': self.get_return_url(request, expense),
                },
            )

        parts_input = form.get_parts(involved_people)

        custom_total = sum((v['should_pay'] for v in parts_input.values() if v['should_pay'] is not None), Decimal('0'))
        auto_count = sum(1 for v in parts_input.values() if v['should_pay'] is None)
        payment_total = sum((v['has_paid'] for v in parts_input.values()), Decimal('0'))

        remaining = amount - custom_total
        split_part = Decimal('0')
        remainder = Decimal('0')
        if auto_count:
            split_part = (remaining / auto_count).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
            remainder = remaining - (split_part * auto_count)

        computed_total = custom_total + (split_part * auto_count) + remainder
        if computed_total != amount:
            form.add_error(
                None,
                f'The assigned shares ({computed_total}) do not add up to the expense amount ({amount}). '
                'Mark at least one involved person as auto-split, or adjust the custom shares.',
            )
        if payment_total != amount:
            form.add_error(
                None,
                f'The amounts paid ({payment_total}) do not add up to the expense amount ({amount}).',
            )

        if form.errors:
            return render(
                request,
                'netbox_ledger_tracker/expense_split.html',
                {
                    'form': form,
                    'expense': expense,
                    'ledger': ledger,
                    'return_url': self.get_return_url(request, expense),
                },
            )

        with transaction.atomic():
            if expense is None:
                expense = Expense()
            expense.name = form.cleaned_data['name']
            expense.ledger = ledger
            expense.currency = currency
            expense.amount = amount
            expense.date = form.cleaned_data['date']
            expense.comments = form.cleaned_data.get('comments', '')
            expense.full_clean()
            expense.save()

            expense.parts.all().delete()
            remaining_to_absorb = remainder
            for person, part_data in parts_input.items():
                if part_data['should_pay'] is None:
                    share = split_part + remaining_to_absorb
                    remaining_to_absorb = Decimal('0')
                else:
                    share = part_data['should_pay']
                # The *_native columns are derived by ExpensePart.save() from the
                # expense's frozen rate, so they are deliberately not set here.
                part = ExpensePart(
                    expense=expense,
                    person=person,
                    has_paid=part_data['has_paid'],
                    should_pay=share,
                    auto_amount=part_data['should_pay'] is None,
                )
                part.full_clean()
                part.save()

        messages.success(request, f'Saved expense "{expense.name}" split between {len(parts_input)} people.')
        return redirect(self.get_return_url(request, expense))


###
# ExpensePart
###


@register_model_view(ExpensePart)
class ExpensePartView(ObjectView):
    actions = (EditObject, DeleteObject)
    queryset = ExpensePart.objects.select_related('expense', 'person').prefetch_related('tags')
    template_name = 'netbox_ledger_tracker/expensepart.html'
    layout = SimpleLayout(
        left_panels=[ExpensePartPanel()],
        right_panels=[TemplatePanel('inc/panels/tags.html')],
    )


@register_model_view(ExpensePart, name='list', path='', detail=False)
class ExpensePartListView(ObjectListView):
    queryset = ExpensePart.objects.select_related('expense', 'person')
    table = ExpensePartTable
    filterset = ExpensePartFilterSet
    filterset_form = ExpensePartFilterForm


@register_model_view(ExpensePart, name='add', detail=False)
@register_model_view(ExpensePart, name='edit')
class ExpensePartEditView(ObjectEditView):
    queryset = ExpensePart.objects.all()
    form = ExpensePartForm


@register_model_view(ExpensePart, name='delete')
class ExpensePartDeleteView(ObjectDeleteView):
    queryset = ExpensePart.objects.all()


@register_model_view(ExpensePart, name='bulk_edit', path='edit', detail=False)
class ExpensePartBulkEditView(BulkEditView):
    queryset = ExpensePart.objects.all()
    table = ExpensePartTable
    form = ExpensePartBulkEditForm


@register_model_view(ExpensePart, name='bulk_delete', path='delete', detail=False)
class ExpensePartBulkDeleteView(BulkDeleteView):
    queryset = ExpensePart.objects.all()
    table = ExpensePartTable


###
# Settlement
###


@register_model_view(Settlement)
class SettlementView(ObjectView):
    actions = (CloneObject, EditObject, DeleteObject)
    queryset = Settlement.objects.select_related('ledger', 'from_person', 'to_person', 'currency').prefetch_related(
        'tags'
    )
    layout = SimpleLayout(
        left_panels=[SettlementPanel()],
        right_panels=[TemplatePanel('inc/panels/tags.html')],
    )


@register_model_view(Settlement, name='list', path='', detail=False)
class SettlementListView(ObjectListView):
    queryset = Settlement.objects.select_related('ledger', 'from_person', 'to_person', 'currency')
    table = SettlementTable
    filterset = SettlementFilterSet
    filterset_form = SettlementFilterForm


@register_model_view(Settlement, name='add', detail=False)
@register_model_view(Settlement, name='edit')
class SettlementEditView(ObjectEditView):
    queryset = Settlement.objects.all()
    form = SettlementForm


@register_model_view(Settlement, name='delete')
class SettlementDeleteView(ObjectDeleteView):
    queryset = Settlement.objects.all()


@register_model_view(Settlement, name='bulk_import', path='import', detail=False)
class SettlementBulkImportView(BulkImportView):
    queryset = Settlement.objects.all()
    model_form = SettlementImportForm


@register_model_view(Settlement, name='bulk_edit', path='edit', detail=False)
class SettlementBulkEditView(BulkEditView):
    queryset = Settlement.objects.all()
    table = SettlementTable
    form = SettlementBulkEditForm


@register_model_view(Settlement, name='bulk_delete', path='delete', detail=False)
class SettlementBulkDeleteView(BulkDeleteView):
    queryset = Settlement.objects.all()
    table = SettlementTable
