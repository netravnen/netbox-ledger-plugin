"""REST API viewsets for netbox_ledger_tracker models."""

from netbox.api.viewsets import NetBoxModelViewSet

from .. import filtersets, models
from . import serializers


class CurrencyViewSet(NetBoxModelViewSet):
    queryset = models.Currency.objects.prefetch_related('tags')
    serializer_class = serializers.CurrencySerializer
    filterset_class = filtersets.CurrencyFilterSet


class LedgerViewSet(NetBoxModelViewSet):
    queryset = models.Ledger.objects.select_related('currency').prefetch_related('tags')
    serializer_class = serializers.LedgerSerializer
    filterset_class = filtersets.LedgerFilterSet


class PersonViewSet(NetBoxModelViewSet):
    queryset = models.Person.objects.select_related('ledger', 'user').prefetch_related('tags')
    serializer_class = serializers.PersonSerializer
    filterset_class = filtersets.PersonFilterSet


class ExpenseViewSet(NetBoxModelViewSet):
    queryset = models.Expense.objects.select_related('ledger', 'currency').prefetch_related('tags')
    serializer_class = serializers.ExpenseSerializer
    filterset_class = filtersets.ExpenseFilterSet


class ExpensePartViewSet(NetBoxModelViewSet):
    queryset = models.ExpensePart.objects.select_related('expense', 'person').prefetch_related('tags')
    serializer_class = serializers.ExpensePartSerializer
    filterset_class = filtersets.ExpensePartFilterSet


class SettlementViewSet(NetBoxModelViewSet):
    queryset = models.Settlement.objects.select_related(
        'ledger', 'from_person', 'to_person', 'currency'
    ).prefetch_related('tags')
    serializer_class = serializers.SettlementSerializer
    filterset_class = filtersets.SettlementFilterSet
