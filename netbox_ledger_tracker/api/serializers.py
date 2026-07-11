"""REST API serializers for netbox_ledger_tracker models."""

from django.contrib.auth import get_user_model
from netbox.api.serializers import NetBoxModelSerializer
from rest_framework import serializers
from users.api.serializers import UserSerializer

from ..models import Currency, Expense, ExpensePart, Ledger, Person

User = get_user_model()


class CurrencySerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:netbox_ledger_tracker-api:currency-detail')

    class Meta:
        model = Currency
        fields = [
            'id',
            'url',
            'display',
            'iso4217_code',
            'base_rate',
            'comments',
            'tags',
            'custom_fields',
            'created',
            'last_updated',
        ]
        brief_fields = ['id', 'url', 'display', 'iso4217_code']


class LedgerSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:netbox_ledger_tracker-api:ledger-detail')
    currency = CurrencySerializer(nested=True)

    class Meta:
        model = Ledger
        fields = [
            'id',
            'url',
            'display',
            'name',
            'currency',
            'closed',
            'calc_method',
            'comments',
            'tags',
            'custom_fields',
            'created',
            'last_updated',
        ]
        brief_fields = ['id', 'url', 'display', 'name']


class PersonSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:netbox_ledger_tracker-api:person-detail')
    ledger = LedgerSerializer(nested=True)
    user = UserSerializer(nested=True, required=False, allow_null=True)

    class Meta:
        model = Person
        fields = [
            'id',
            'url',
            'display',
            'name',
            'ledger',
            'user',
            'tags',
            'custom_fields',
            'created',
            'last_updated',
        ]
        brief_fields = ['id', 'url', 'display', 'name']


class ExpenseSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:netbox_ledger_tracker-api:expense-detail')
    ledger = LedgerSerializer(nested=True)
    currency = CurrencySerializer(nested=True)

    class Meta:
        model = Expense
        fields = [
            'id',
            'url',
            'display',
            'name',
            'ledger',
            'currency',
            'amount',
            'amount_native',
            'date',
            'comments',
            'tags',
            'custom_fields',
            'created',
            'last_updated',
        ]
        brief_fields = ['id', 'url', 'display', 'name']


class ExpensePartSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:netbox_ledger_tracker-api:expensepart-detail')
    expense = ExpenseSerializer(nested=True)
    person = PersonSerializer(nested=True)

    class Meta:
        model = ExpensePart
        fields = [
            'id',
            'url',
            'display',
            'expense',
            'person',
            'has_paid',
            'has_paid_native',
            'should_pay',
            'should_pay_native',
            'auto_amount',
            'tags',
            'custom_fields',
            'created',
            'last_updated',
        ]
        brief_fields = ['id', 'url', 'display']
