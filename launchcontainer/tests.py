"""
Tests for launchcontainer
"""
import json
import mock
import unittest

from xblock.field_data import DictFieldData
from opaque_keys.edx.locations import Location, SlashSeparatedCourseKey

from django.test import modify_settings

from .launchcontainer import DEFAULT_WHARF_ENDPOINT


WHARF_ENDPOINT_GOOD = "https://api.org.com"
WHARF_ENDPOINT_BAD = "notARealUrl"
WHARF_ENDPOINT_UNSET = ""


class DummyResource(object):
    """
     A Resource class for use in tests
    """
    def __init__(self, path):
        self.path = path

    def __eq__(self, other):
        return isinstance(other, DummyResource) and self.path == other.path


class LaunchContainerXBlockTests(unittest.TestCase):
    """
    Create a launchcontainer block with mock data.
    """
    def setUp(self):
        """
        Creates a test course ID, mocks the runtime, and creates a fake storage
        engine for use in all tests
        """
        super(LaunchContainerXBlockTests, self).setUp()
        self.course_id = SlashSeparatedCourseKey.from_deprecated_string(
            'foo/bar/baz'
        )
        self.runtime = mock.Mock(anonymous_student_id='MOCK')
        self.scope_ids = mock.Mock()

    def make_one(self, display_name=None, **kw):
        """
        Creates a launchcontainer XBlock for testing purpose.
        """
        from launchcontainer import LaunchContainerXBlock as cls
        field_data = DictFieldData(kw)
        block = cls(self.runtime, field_data, self.scope_ids)
        block.location = Location(
            'org', 'course', 'run', 'category', 'name', 'revision'
        )
        block.xmodule_runtime = self.runtime
        block.course_id = self.course_id
        block.scope_ids.usage_id = 'XXX'

        if display_name:
            block.display_name = display_name

        block.project = 'Foo project'
        block.project_friendly = 'Foo Project Friendly Name'
        block.project_token = 'Foo token'
        return block

    @mock.patch('launchcontainer.launchcontainer.load_resource', DummyResource)
    @mock.patch('launchcontainer.launchcontainer.render_template')
    @mock.patch('launchcontainer.launchcontainer.Fragment')
    def test_student_view(self, fragment, render_template):
        # pylint: disable=unused-argument
        """
        Test student view renders correctly.
        """
        block = self.make_one("Custom name")
        fragment = block.student_view()
        render_template.assert_called_once()
        template_arg = render_template.call_args_list[0][0][0]
        self.assertEqual(
            template_arg,
            'static/html/launchcontainer.html'
        )
        context = render_template.call_args_list[0][0][1]
        self.assertEqual(context['project'], 'Foo project')
        self.assertEqual(context['project_friendly'], 'Foo Project Friendly Name')
        self.assertEqual(context['user_email'], None)
        fragment.initialize_js.assert_called_once_with(
            "LaunchContainerXBlock")

    @mock.patch('launchcontainer.launchcontainer.load_resource', DummyResource)
    @mock.patch('launchcontainer.launchcontainer.render_template')
    @mock.patch('launchcontainer.launchcontainer.Fragment')
    def test_studio_view(self, fragment, render_template):
        # pylint: disable=unused-argument
        """
        Test that the template, css and javascript are loaded properly into the studio view.
        """
        block = self.make_one()
        fragment = block.studio_view()

        # Called once for the template, once for the css.
        self.assertEqual(render_template.call_count, 2)

        # Confirm that the rendered template is the right one.
        self.assertEqual(
            render_template.call_args_list[0][0][0],
            'static/html/launchcontainer_edit.html'
        )

        # Confirm that the context was set properly on the XBlock instance.
        cls = type(block)
        context = render_template.call_args_list[0][0][1]
        self.assertEqual(tuple(context['fields']), (
            (cls.project, 'Foo project', 'string'),
            (cls.project_friendly, 'Foo Project Friendly Name', 'string'),
            (cls.project_token, 'Foo token', 'string')
        ))

        # Confirm that the JavaScript was pulled in.
        fragment.add_javascript.assert_called_once_with(
            DummyResource("static/js/src/launchcontainer_edit.js"))
        fragment.initialize_js.assert_called_once_with(
            "LaunchContainerEditBlock")

        # Confirm that the css was pulled in.
        fragment.add_css.assert_called_once_with(
            render_template(
                DummyResource("static/js/src/launchcontainer_edit.css")
            )
        )

        css_template_arg = render_template.call_args_list[1][0][0]
        self.assertEqual(
            css_template_arg,
            'static/css/launchcontainer_edit.css'
        )

    def test_save_launchcontainer(self):
        """
        Tests save launchcontainer block on studio.
        """
        proj_str = 'Baz Project shortname'
        proj_friendly_str = 'Baz Project Friendly Name'
        block = self.make_one()
        block.studio_submit(mock.Mock(body='{}'))
        self.assertEqual(block.display_name, "Container Launcher")
        self.assertEqual(block.project, 'Foo project')
        self.assertEqual(block.project_friendly, 'Foo Project Friendly Name')
        block.studio_submit(mock.Mock(method="POST", body=json.dumps({
            "project": proj_str,
            "project_friendly": proj_friendly_str})))
        self.assertEqual(block.display_name, "Container Launcher")

    @modify_settings(ENV_TOKENS={
        'LAUNCHCONTAINER_API_CONF': WHARF_ENDPOINT_GOOD
    })
    def test_api_url_set_defined_with_org(self):
        """
        Test expected case with ENV TOKEN for DEFAULT_WHARF_ENDPOINT
        """
        block = self.make_one()
        block.studio_submit(mock.Mock(body='{}'))
        self.assertEqual(block.api_url, 'https://api.org.com')

    @modify_settings(ENV_TOKENS={
        'LAUNCHCONTAINER_API_CONF': WHARF_ENDPOINT_BAD
    })
    def test_api_url_default_fallback(self):
        """
        Test expected case with ENV TOKEN for DEFAULT_WHARF_ENDPOINT
        """
        block = self.make_one()
        block.studio_submit(mock.Mock(body='{}'))
        self.assertEqual(block.api_url, 'https://api.default.com')

    @modify_settings(ENV_TOKENS={
        'LAUNCHCONTAINER_API_CONF': WHARF_ENDPOINT_UNSET
    })
    def test_api_url_not_set(self):
        """
        Test expected case with ENV TOKEN for DEFAULT_WHARF_ENDPOINT
        """
        block = self.make_one()
        block.studio_submit(mock.Mock(body='{}'))
        self.assertEqual(block.api_url, DEFAULT_WHARF_ENDPOINT)
