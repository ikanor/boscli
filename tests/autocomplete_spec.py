# -*- coding: utf-8 -*-

from mamba import *
from hamcrest import *
from doublex import *

import boscli
from boscli import parser as parser_module
from boscli import interpreter as interpreter_module
from boscli import completer as completer_module
from boscli import basic_types

with describe('Autocomplete') as _:

    @before.each
    def set_up():
        parser = parser_module.Parser()
        _.interpreter = interpreter_module.Interpreter(parser)
        _.completer = completer_module.Completer(_.interpreter, parser)
        _.implementation = Stub()

        _.interpreter.add_command(boscli.Command(['sys', 'reboot'], _.implementation.reboot))
        _.interpreter.add_command(boscli.Command(['sys', 'shutdown'], _.implementation.shutdown))
        _.interpreter.add_command(boscli.Command(['net', 'show', 'configuration'], _.implementation.show_net_conf))

    with describe('when autocompleting empty line'):
        def it_complete_with_initial_keywords():
            assert_that(_.completer.complete(''), has_items('sys ', 'net '))

    with describe('when autocompleting keywords'):

        def it_complete_keywords():
            assert_that(_.completer.complete('sy'), has_items('sys '))
            assert_that(_.completer.complete('sys'), has_items('sys '))
            assert_that(_.completer.complete('sys r'), has_items('reboot '))

        def it_not_complete_when_a_command_match():
            assert_that(_.completer.complete('sys reboot'), has_length(0))

        def it_not_complete_unknown_command():
            assert_that(_.completer.complete('unknown command'), has_length(0))

    with describe('when autocompleting options type'):
        def it_complete_with_all_matching_options():
            _.interpreter.add_command(boscli.Command(['cmd', basic_types.OptionsType(['op1', 'op2'])],
                                    _.implementation.show_net_conf))

            assert_that(_.completer.complete('cmd o'), has_items('op1', 'op2'))

    with describe('when autocompleting a string type'):
        def it_no_autocomplete_at_all():
            _.interpreter.add_command(boscli.Command(['cmd', basic_types.StringType()],
                                        _.implementation.show_net_conf))

            assert_that(_.completer.complete('cmd '), has_length(0))
