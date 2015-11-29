# -*- coding: utf-8 -*-

import sys
from boscli import exceptions
from boscli import parser as parser_module
from boscli import filters


class Context(object):

    def __init__(self, context_name, prompt=None):
        self.context_name = context_name
        self._prompt = prompt
        self.data = {}

    def has_name(self, context_name):
        return self.context_name == context_name

    @property
    def prompt(self):
        if self._prompt:
            return self._prompt
        return self.context_name

    def __str__(self):
        return "Context%s" % self.context_name


class Interpreter(object):

    def __init__(self,
                 parser=parser_module.Parser(),
                 filter_factory=filters.FilterFactory(),
                 output_stream=sys.stdout,
                 prompt=''):
        self._commands = []
        self.parser = parser
        self.context = []
        self._prompt = prompt
        self.filter_factory = filter_factory
        self.output_stream = output_stream

    def add_command(self, command):
        self._commands.append(command)

    def push_context(self, context_name, prompt=None):
        self.context.append(Context(context_name, prompt))

    def pop_context(self):
        try:
            self.context.pop()
        except IndexError:
            raise exceptions.NotContextDefinedError()

    def exit(self):
        raise exceptions.EndOfProgram()

    def _extract_command_and_filter(self, tokens):
        FILTER_SEP = '|'
        command = []
        filter_command = []
        sep_found = False
        for token in tokens:
            if token == FILTER_SEP:
                if sep_found:
                    raise exceptions.SintaxError()
                sep_found = True
                continue
            if sep_found:
                filter_command.append(token)
            else:
                command.append(token)
        return command, filter_command or None, sep_found

    def _filter_command(self, filter_tokens):
        try:
            if 'include'.startswith(filter_tokens[0]):
                return self.filter_factory.create_include_filter(filter_tokens[1], self.output_stream)
            if 'exclude'.startswith(filter_tokens[0]):
                return self.filter_factory.create_exclude_filter(filter_tokens[1], self.output_stream)
            raise exceptions.SintaxError()
        except IndexError:
            raise exceptions.SintaxError()

    def _matching_command(self, tokens, line_text):
        perfect_matching_commands = self._select_perfect_matching_commands(tokens)
        if len(perfect_matching_commands) == 1:
            return perfect_matching_commands[0]

        matching_commands = self._select_matching_commands(tokens)
        if len(matching_commands) == 1:
            return matching_commands[0]

        if len(matching_commands) > 0:
            raise exceptions.AmbiguousCommandError(matching_commands)
        raise exceptions.NotMatchingCommandFoundError(line_text)

    def eval_multiple(self, lines):
        results = []
        for line in lines:
            results.append(self.eval(line))
        return results

    def eval(self, line_text):
        line_text = line_text.strip()
        if not line_text:
            return

        tokens, filter_tokens, _ = self._extract_command_and_filter(
            self.parser.parse(line_text))
        matching_command = self._matching_command(tokens, line_text)

        if not filter_tokens:
            return self._execute_command(matching_command, matching_command.normalize_tokens(tokens, self.actual_context()))

        output_filter = self._filter_command(filter_tokens)
        with filters.RedirectStdout(output_filter):
            return self._execute_command(matching_command, matching_command.normalize_tokens(tokens, self.actual_context()))


    def _execute_command(self, command, tokens):
        arguments = command.matching_parameters(tokens)
        try:
            return command.execute(*arguments, tokens=tokens, interpreter=self)
        except KeyboardInterrupt:
            pass

    def _select_perfect_matching_commands(self, tokens):
        return [command for command in self._commands if command.perfect_match(tokens, self.actual_context())]

    def _select_matching_commands(self, tokens):
        return [command for command in self._commands if command.match(tokens, self.actual_context())]

    def actual_context(self):
        if len(self.context) > 0:
            return self.context[-1]
        return None

    def active_commands(self):
        return [command for command in self._commands if command.context_match(self.actual_context())]

    def _partial_match(self, line_text):
        tokens = self.parser.parse(line_text)
        return [command for command in self.active_commands() if command.partial_match(tokens, self.actual_context())]

    def help(self, line_text):
        return {command: command.help for command in self._partial_match(line_text)}

    def complete(self, line_to_complete):
        completions = set()
        tokens, filter_tokens, sep_found = self._extract_command_and_filter(
            self.parser.parse(line_to_complete))
        if filter_tokens:
            return {option for option in ['include', 'exclude'] if option.startswith(filter_tokens[-1])}
        if sep_found:
            return {' '}

        for command in self._partial_match(line_to_complete):
            if command not in self._select_perfect_matching_commands(tokens):
                completions.update(command.complete(tokens, self.actual_context()))
        return completions

    @property
    def prompt(self):
        return self.actual_context().prompt if self.actual_context() else self._prompt

    @prompt.setter
    def prompt(self, value):
        self._prompt = value
