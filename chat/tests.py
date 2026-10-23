import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.test import TestCase
from .models import Item
from .tools import calculate_cost, set_price


class PricingTests(TestCase):
    def setUp(self):
        self.item = Item.objects.create(name="Chocolate bar", quantity=20, price="2.50")

    def test_assignment_quote(self):
        result = calculate_cost("chocolate BAR", 3, 10)
        self.assertEqual((result['subtotal'], result['vat_amount'], result['total']), ('7.50', '0.75', '8.25'))
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 20)

    def test_missing_price_and_item(self):
        self.assertIn('error', calculate_cost('Unknown', 3, 10))
        self.item.price = None
        self.item.save()
        self.assertIn('error', calculate_cost('Chocolate bar', 3, 10))

    def test_invalid_inputs(self):
        for qty in [0, -1, 1.5, True]:
            self.assertIn('error', calculate_cost('Chocolate bar', qty, 10))
        for vat in [-1, 101, 'NaN', 'Infinity', 'abc']:
            self.assertIn('error', calculate_cost('Chocolate bar', 3, vat))
        for price in ['-1', '1.234', 'NaN', 'Infinity', '100000000']:
            self.assertIn('error', set_price('Chocolate bar', price))

    def test_set_price_and_rounding(self):
        self.assertEqual(set_price('Chocolate bar', '0.05')['price'], '0.05')
        self.assertEqual(calculate_cost('Chocolate bar', 1, 10)['total'], '0.06')
        self.assertEqual(calculate_cost('Chocolate bar', 1, 0)['total'], '0.05')
        self.assertEqual(set_price('Chocolate bar', '0')['price'], '0.00')
        self.assertIn('error', set_price('Unknown', '1.00'))

    def test_negative_price_model_validation(self):
        self.item.price = Decimal('-1')
        with self.assertRaises(ValidationError):
            self.item.full_clean()

    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'})
    @patch('chat.agent.genai.Client')
    def test_chat_tool_roundtrip(self, client_class):
        call = SimpleNamespace(type='function_call', name='calculate_cost', id='call1', arguments={
            'name': 'Chocolate bar', 'quantity': 3, 'vat_percent': 10})
        api = client_class.return_value.interactions
        api.create.side_effect = [
            SimpleNamespace(steps=[call], id='first'),
            SimpleNamespace(steps=[], output_text='3 chocolate bars cost 8.25 including 0.75 VAT.', id='second'),
        ]
        response = self.client.post('/', {'message': 'What is the cost of 3 items of chocolate bar after adding 10% VAT?'}, follow=True)
        self.assertContains(response, '8.25')
        returned = api.create.call_args.kwargs['input'][0]
        self.assertEqual(json.loads(returned['result'][0]['text'])['total'], '8.25')
        self.assertEqual(self.client.session['interaction_id'], 'second')
