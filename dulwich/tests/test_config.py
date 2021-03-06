# test_config.py -- Tests for reading and writing configuration files
# Copyright (C) 2011 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# or (at your option) a later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Tests for reading and writing configuraiton files."""

from cStringIO import StringIO
from dulwich.config import (
    ConfigDict,
    ConfigFile,
    StackedConfig,
    _check_section_name,
    _check_variable_name,
    _format_string,
    _escape_value,
    _parse_string,
    _unescape_value,
    )
from dulwich.tests import TestCase
import os


class ConfigFileTests(TestCase):

    def from_file(self, text):
        return ConfigFile.from_file(StringIO(text))

    def test_empty(self):
        ConfigFile()

    def test_eq(self):
        self.assertEquals(ConfigFile(), ConfigFile())

    def test_default_config(self):
        cf = self.from_file("""[core]
	repositoryformatversion = 0
	filemode = true
	bare = false
	logallrefupdates = true
""")
        self.assertEquals(ConfigFile({("core", ): {
            "repositoryformatversion": "0",
            "filemode": "true",
            "bare": "false",
            "logallrefupdates": "true"}}), cf)

    def test_from_file_empty(self):
        cf = self.from_file("")
        self.assertEquals(ConfigFile(), cf)

    def test_empty_line_before_section(self):
        cf = self.from_file("\n[section]\n")
        self.assertEquals(ConfigFile({("section", ): {}}), cf)

    def test_comment_before_section(self):
        cf = self.from_file("# foo\n[section]\n")
        self.assertEquals(ConfigFile({("section", ): {}}), cf)

    def test_comment_after_section(self):
        cf = self.from_file("[section] # foo\n")
        self.assertEquals(ConfigFile({("section", ): {}}), cf)

    def test_comment_after_variable(self):
        cf = self.from_file("[section]\nbar= foo # a comment\n")
        self.assertEquals(ConfigFile({("section", ): {"bar": "foo"}}), cf)

    def test_from_file_section(self):
        cf = self.from_file("[core]\nfoo = bar\n")
        self.assertEquals("bar", cf.get(("core", ), "foo"))
        self.assertEquals("bar", cf.get(("core", "foo"), "foo"))

    def test_from_file_section_case_insensitive(self):
        cf = self.from_file("[cOre]\nfOo = bar\n")
        self.assertEquals("bar", cf.get(("core", ), "foo"))
        self.assertEquals("bar", cf.get(("core", "foo"), "foo"))

    def test_from_file_with_mixed_quoted(self):
        cf = self.from_file("[core]\nfoo = \"bar\"la\n")
        self.assertEquals("barla", cf.get(("core", ), "foo"))

    def test_from_file_with_open_quoted(self):
        self.assertRaises(ValueError,
            self.from_file, "[core]\nfoo = \"bar\n")

    def test_from_file_with_quotes(self):
        cf = self.from_file(
            "[core]\n"
            'foo = " bar"\n')
        self.assertEquals(" bar", cf.get(("core", ), "foo"))

    def test_from_file_with_interrupted_line(self):
        cf = self.from_file(
            "[core]\n"
            'foo = bar\\\n'
            ' la\n')
        self.assertEquals("barla", cf.get(("core", ), "foo"))

    def test_from_file_with_boolean_setting(self):
        cf = self.from_file(
            "[core]\n"
            'foo\n')
        self.assertEquals("true", cf.get(("core", ), "foo"))

    def test_from_file_subsection(self):
        cf = self.from_file("[branch \"foo\"]\nfoo = bar\n")
        self.assertEquals("bar", cf.get(("branch", "foo"), "foo"))

    def test_from_file_subsection_invalid(self):
        self.assertRaises(ValueError,
            self.from_file, "[branch \"foo]\nfoo = bar\n")

    def test_from_file_subsection_not_quoted(self):
        cf = self.from_file("[branch.foo]\nfoo = bar\n")
        self.assertEquals("bar", cf.get(("branch", "foo"), "foo"))

    def test_write_to_file_empty(self):
        c = ConfigFile()
        f = StringIO()
        c.write_to_file(f)
        self.assertEquals("", f.getvalue())

    def test_write_to_file_section(self):
        c = ConfigFile()
        c.set(("core", ), "foo", "bar")
        f = StringIO()
        c.write_to_file(f)
        self.assertEquals("[core]\nfoo = bar\n", f.getvalue())

    def test_write_to_file_subsection(self):
        c = ConfigFile()
        c.set(("branch", "blie"), "foo", "bar")
        f = StringIO()
        c.write_to_file(f)
        self.assertEquals("[branch \"blie\"]\nfoo = bar\n", f.getvalue())

    def test_same_line(self):
        cf = self.from_file("[branch.foo] foo = bar\n")
        self.assertEquals("bar", cf.get(("branch", "foo"), "foo"))


class ConfigDictTests(TestCase):

    def test_get_set(self):
        cd = ConfigDict()
        self.assertRaises(KeyError, cd.get, "foo", "core")
        cd.set(("core", ), "foo", "bla")
        self.assertEquals("bla", cd.get(("core", ), "foo"))
        cd.set(("core", ), "foo", "bloe")
        self.assertEquals("bloe", cd.get(("core", ), "foo"))

    def test_get_boolean(self):
        cd = ConfigDict()
        cd.set(("core", ), "foo", "true")
        self.assertTrue(cd.get_boolean(("core", ), "foo"))
        cd.set(("core", ), "foo", "false")
        self.assertFalse(cd.get_boolean(("core", ), "foo"))
        cd.set(("core", ), "foo", "invalid")
        self.assertRaises(ValueError, cd.get_boolean, ("core", ), "foo")


class StackedConfigTests(TestCase):

    def test_default_backends(self):
        self.addCleanup(os.environ.__setitem__, "HOME", os.environ["HOME"])
        os.environ["HOME"] = "/nonexistant"
        StackedConfig.default_backends()


class UnescapeTests(TestCase):

    def test_nothing(self):
        self.assertEquals("", _unescape_value(""))

    def test_tab(self):
        self.assertEquals("\tbar\t", _unescape_value("\\tbar\\t"))

    def test_newline(self):
        self.assertEquals("\nbar\t", _unescape_value("\\nbar\\t"))

    def test_quote(self):
        self.assertEquals("\"foo\"", _unescape_value("\\\"foo\\\""))


class EscapeValueTests(TestCase):

    def test_nothing(self):
        self.assertEquals("foo", _escape_value("foo"))

    def test_backslash(self):
        self.assertEquals("foo\\\\", _escape_value("foo\\"))

    def test_newline(self):
        self.assertEquals("foo\\n", _escape_value("foo\n"))


class FormatStringTests(TestCase):

    def test_quoted(self):
        self.assertEquals('" foo"', _format_string(" foo"))
        self.assertEquals('"\\tfoo"', _format_string("\tfoo"))

    def test_not_quoted(self):
        self.assertEquals('foo', _format_string("foo"))
        self.assertEquals('foo bar', _format_string("foo bar"))


class ParseStringTests(TestCase):

    def test_quoted(self):
        self.assertEquals(' foo', _parse_string('" foo"'))
        self.assertEquals('\tfoo', _parse_string('"\\tfoo"'))

    def test_not_quoted(self):
        self.assertEquals('foo', _parse_string("foo"))
        self.assertEquals('foo bar', _parse_string("foo bar"))


class CheckVariableNameTests(TestCase):

    def test_invalid(self):
        self.assertFalse(_check_variable_name("foo "))
        self.assertFalse(_check_variable_name("bar,bar"))
        self.assertFalse(_check_variable_name("bar.bar"))

    def test_valid(self):
        self.assertTrue(_check_variable_name("FOO"))
        self.assertTrue(_check_variable_name("foo"))
        self.assertTrue(_check_variable_name("foo-bar"))


class CheckSectionNameTests(TestCase):

    def test_invalid(self):
        self.assertFalse(_check_section_name("foo "))
        self.assertFalse(_check_section_name("bar,bar"))

    def test_valid(self):
        self.assertTrue(_check_section_name("FOO"))
        self.assertTrue(_check_section_name("foo"))
        self.assertTrue(_check_section_name("foo-bar"))
        self.assertTrue(_check_section_name("bar.bar"))
