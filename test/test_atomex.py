# pylint: disable=no-member

from os.path import dirname, join
from unittest import TestCase

from pytezos import ContractInterface
from pytezos.standards.nyx import NYXTokenImpl
from pytezos.repl.parser import MichelsonRuntimeError

nyx_address = 'KT1TjdF4H8H2qzxichtEbiCwHxCRM1SVx6B7'  # just some valid address
source = 'tz1cShoBMAfpWX35DUcQRsXbqAgWAB4tz7kj'
another_source = 'tz1grSQDByRpnVs7sPtaprNZRp531ZKz6Jmm'
party = 'tz1h3rQ8wBxFd8L9B3d7Jhaawu6Z568XU3xY'
proxy = 'tz1grSQDByRpnVs7sPtaprNZRp531ZKz6Jmm'
secret = 'dca15ce0c01f61ab03139b4673f4bd902203dc3b898a89a5d35bad794e5cfd4f'
hashed_secret = '05bce5c12071fbca95b13d49cb5ef45323e0216d618bb4575c519b74be75e3da'
empty_storage = {}
project_dir = dirname(dirname(__file__))


class AtomexContractTest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.atomex = ContractInterface.create_from(join(project_dir, 'src/atomex.tz'))
        cls.nyx = NYXTokenImpl.interface()
        cls.maxDiff = None

    def assertTransfer(self, parameters, amount, tr_to):
        params = self.nyx.parameter.decode(parameters)
        self.assertEqual({'transfer': [{
            'amount': amount,
            'tr_to': tr_to
        }]}, params)

    def assertTransferFrom(self, parameters, amount, tr_from, tr_to):
        params = self.nyx.parameter.decode(parameters)
        self.assertEqual({'transferFrom': [{
            'amount': amount,
            'tr_from': tr_from,
            'tr_to': tr_to
        }]}, params)

    def test_no_tez(self):
        with self.assertRaises(MichelsonRuntimeError):
            self.atomex \
                .initiate(hashedSecret=hashed_secret,
                          participant=party,
                          refundTime=6 * 3600,
                          tokenAddress=nyx_address,
                          totalAmount=1000) \
                .interpret(storage=empty_storage,
                           source=source,
                           amount=1000,
                           now=0)

    def test_initiate(self):
        res = self.atomex \
            .initiate(hashedSecret=hashed_secret,
                      participant=party,
                      refundTime=6 * 3600,
                      tokenAddress=nyx_address,
                      totalAmount=1000) \
            .interpret(storage=empty_storage,
                       source=source,
                       now=0)

        big_map_diff = {
            hashed_secret: {
                'initiator': source,
                'participant': party,
                'refundTime': 6 * 3600,
                'tokenAddress': nyx_address,
                'totalAmount': 1000
            }
        }
        self.assertDictEqual(big_map_diff, res.big_map_diff)
        self.assertEqual(1, len(res.operations))
        self.assertTransferFrom(
            parameters=res.operations[0]['parameters'],
            amount=1000,
            tr_from=source,
            tr_to=res.operations[0]['source'])

    def test_initiate_proxy(self):
        res = self.atomex \
            .initiate(hashedSecret=hashed_secret,
                      participant=party,
                      refundTime=6 * 3600,
                      tokenAddress=nyx_address,
                      totalAmount=1000) \
            .interpret(storage=empty_storage,
                       sender=proxy,
                       source=source,
                       now=0)

        big_map_diff = {
            hashed_secret: {
                'initiator': proxy,
                'participant': party,
                'refundTime': 6 * 3600,
                'tokenAddress': nyx_address,
                'totalAmount': 1000
            }
        }
        self.assertDictEqual(big_map_diff, res.big_map_diff)
        self.assertEqual(1, len(res.operations))
        self.assertTransferFrom(
            parameters=res.operations[0]['parameters'],
            amount=1000,
            tr_from=proxy,
            tr_to=res.operations[0]['source'])

    def test_initiate_same_secret(self):
        initial_storage = {
            hashed_secret: {
                'initiator': proxy,
                'participant': party,
                'refundTime': 6 * 3600,
                'tokenAddress': nyx_address,
                'totalAmount': 1000
            }
        }

        with self.assertRaises(MichelsonRuntimeError):
            self.atomex \
                .initiate(hashedSecret=hashed_secret,
                          participant=party,
                          refundTime=6 * 3600,
                          tokenAddress=nyx_address,
                          totalAmount=1000) \
                .interpret(storage=initial_storage,
                           source=source,
                           now=0)

    def test_initiate_in_the_past(self):
        now = 1000000000
        with self.assertRaises(MichelsonRuntimeError):
            self.atomex \
                .initiate(hashedSecret=hashed_secret,
                          participant=party,
                          refundTime=6 * 3600,
                          tokenAddress=nyx_address,
                          totalAmount=1000) \
                .interpret(storage=empty_storage,
                           source=source,
                           now=now)

    def test_initiate_party_equals_source(self):
        with self.assertRaises(MichelsonRuntimeError):
            self.atomex \
                .initiate(hashedSecret=hashed_secret,
                          participant=party,
                          refundTime=6 * 3600,
                          tokenAddress=nyx_address,
                          totalAmount=1000) \
                .interpret(storage=empty_storage,
                           sender=proxy,
                           source=party,
                           now=0)

    def test_initiate_party_equals_sender(self):
        with self.assertRaises(MichelsonRuntimeError):
            self.atomex \
                .initiate(hashedSecret=hashed_secret,
                          participant=party,
                          refundTime=6 * 3600,
                          tokenAddress=nyx_address,
                          totalAmount=1000) \
                .interpret(storage=empty_storage,
                           sender=party,
                           source=source,
                           now=0)

    def test_redeem_by_third_party(self):
        initial_storage = {
            hashed_secret: {
                'initiator': source,
                'participant': party,
                'refundTime': 6 * 3600,
                'tokenAddress': nyx_address,
                'totalAmount': 1000
            }
        }

        res = self.atomex \
            .redeem(secret) \
            .interpret(storage=initial_storage,
                       source=source,
                       now=0)

        self.assertDictEqual({hashed_secret: None}, res.big_map_diff)
        self.assertEqual(1, len(res.operations))
        self.assertTransfer(
            parameters=res.operations[0]['parameters'],
            amount=1000,
            tr_to=party)

    def test_redeem_after_expiration(self):
        initial_storage = {
            hashed_secret: {
                'initiator': source,
                'participant': party,
                'refundTime': 0,
                'tokenAddress': nyx_address,
                'totalAmount': 1000
            }
        }

        with self.assertRaises(MichelsonRuntimeError):
            self.atomex \
                .redeem(secret) \
                .interpret(storage=initial_storage,
                           source=party,
                           now=60)

    def test_redeem_invalid_secret(self):
        initial_storage = {
            hashed_secret: {
                'initiator': source,
                'participant': party,
                'refundTime': 60,
                'tokenAddress': nyx_address,
                'totalAmount': 1000
            }
        }

        with self.assertRaises(MichelsonRuntimeError):
            self.atomex \
                .redeem('a' * 32) \
                .interpret(storage=initial_storage,
                           source=source,
                           now=0)

    def test_redeem_with_money(self):
        initial_storage = {
            hashed_secret: {
                'initiator': source,
                'participant': party,
                'refundTime': 60,
                'tokenAddress': nyx_address,
                'totalAmount': 1000
            }
        }

        with self.assertRaises(MichelsonRuntimeError):
            self.atomex \
                .redeem(secret) \
                .with_amount(100000) \
                .interpret(storage=initial_storage,
                           source=source,
                           now=0)

    def test_refund(self):
        initial_storage = {
            hashed_secret: {
                'initiator': source,
                'participant': party,
                'refundTime': 0,
                'tokenAddress': nyx_address,
                'totalAmount': 1000
            }
        }

        res = self.atomex \
            .refund(hashed_secret) \
            .interpret(storage=initial_storage,
                       source=source,
                       now=60)

        self.assertDictEqual({hashed_secret: None}, res.big_map_diff)
        self.assertEqual(1, len(res.operations))
        self.assertTransfer(
            parameters=res.operations[0]['parameters'],
            amount=1000,
            tr_to=source)

    def test_third_party_refund(self):
        initial_storage = {
            hashed_secret: {
                'initiator': source,
                'participant': party,
                'refundTime': 0,
                'tokenAddress': nyx_address,
                'totalAmount': 1000
            }
        }

        res = self.atomex \
            .refund(hashed_secret) \
            .interpret(storage=initial_storage,
                       source=proxy,
                       now=60)

        self.assertDictEqual({hashed_secret: None}, res.big_map_diff)
        self.assertEqual(1, len(res.operations))
        self.assertTransfer(
            parameters=res.operations[0]['parameters'],
            amount=1000,
            tr_to=source)

    def test_refund_before_expiration(self):
        initial_storage = {
            hashed_secret: {
                'initiator': source,
                'participant': party,
                'refundTime': 60,
                'tokenAddress': nyx_address,
                'totalAmount': 1000
            }
        }

        with self.assertRaises(MichelsonRuntimeError):
            self.atomex \
                .refund(hashed_secret) \
                .interpret(storage=initial_storage,
                           source=source,
                           now=0)

    def test_refund_non_existent(self):
        with self.assertRaises(MichelsonRuntimeError):
            self.atomex \
                .refund(hashed_secret) \
                .interpret(storage=empty_storage,
                           source=source,
                           now=0)

    def test_refund_with_money(self):
        initial_storage = {
            hashed_secret: {
                'initiator': source,
                'participant': party,
                'refundTime': 0,
                'tokenAddress': nyx_address,
                'totalAmount': 1000
            }
        }

        with self.assertRaises(MichelsonRuntimeError):
            self.atomex \
                .refund(hashed_secret) \
                .with_amount(100000) \
                .interpret(storage=initial_storage,
                           source=source,
                           now=60)
