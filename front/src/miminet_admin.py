import json

from datetime import date

from flask import request, flash, redirect, url_for
from flask_admin import AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.fields import QuerySelectField
from flask_admin.form import Select2Widget
from flask_admin.model import typefmt
from flask_admin.actions import action
from flask_login import current_user
from markupsafe import Markup
from wtforms import (
    SelectField,
    TextAreaField,
    BooleanField,
    DateTimeField,
    Form,
    SubmitField,
)

from quiz.service.network_upload_service import (
    create_check_task,
    create_check_task_json,
)
from miminet_model import db, User, Network
from quiz.entity.entity import (
    Test,
    Section,
    Question,
    QuestionCategory,
    SessionQuestion,
)

ADMIN_ROLE_LEVEL = 1


class MiminetAdminIndexView(AdminIndexView):
    @expose("/")
    def index(self):
        return self.render("admin/index.html")

    def is_accessible(self):
        if current_user.is_authenticated:
            if current_user.role >= ADMIN_ROLE_LEVEL:
                return True
        else:
            return False

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("login_index"))


# Base model view
class MiminetAdminModelView(ModelView):
    # Remove columns from list view
    column_exclude_list = ["is_deleted", "updated_on"]
    # Remove fields
    form_excluded_columns = ["is_deleted", "updated_on", "created_on"]

    can_set_page_size = True

    def is_accessible(self):
        if current_user.is_authenticated:
            if current_user.role >= ADMIN_ROLE_LEVEL:
                return True
        else:
            return False

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("login_index"))

    def on_model_change(self, form, model, is_created, **kwargs):
        if hasattr(model, "created_by_id"):
            if not is_created and model.created_by_id != current_user.id:
                raise Exception("You are not allowed to edit this record.")
            if is_created:
                model.created_by_id = current_user.id
        else:
            pass

    MY_DEFAULT_FORMATTERS = dict(typefmt.BASE_FORMATTERS)
    MY_DEFAULT_FORMATTERS.update(
        {
            type(None): typefmt.null_formatter,
            date: lambda view, value: value.strftime("%d.%m.%Y"),
        }
    )

    column_type_formatters = MY_DEFAULT_FORMATTERS


def created_by_formatter(view, context, model, name, **kwargs):
    user = User.query.get(model.created_by_id)
    if user and user.nick:
        return user.nick
    raise Exception("Error occurred while retrieving user nickname")


class TestView(MiminetAdminModelView):
    column_list = (
        "name",
        "description",
        "is_ready",
        "is_retakeable",
        "created_on",
        "created_by_id",
    )
    column_sortable_list = ("name", "created_on", "created_by_id")

    column_labels = {
        "name": "Название",
        "description": "Описание",
        "is_ready": "Тест готов",
        "is_retakeable": "Можно перепроходить",
        "created_on": "Дата создания",
        "created_by_id": "Автор",
    }

    column_formatters = {"created_by_id": created_by_formatter}

    pass


def get_test_name(view, context, model, name, **kwargs):
    test = Test.query.get(model.test_id)
    if test and test.name:
        return test.name
    raise Exception("Error occurred while retrieving test name")


class SectionView(MiminetAdminModelView):
    column_list = (
        "test_id",
        "name",
        "description",
        "timer",
        "is_exam",
        "results_available_from",
        "created_on",
        "created_by_id",
        "meta",
    )
    column_sortable_list = ("name", "created_on", "created_by_id", "test_id")

    column_labels = {
        "name": "Название",
        "description": "Описание",
        "timer": "Время на прохождение (в минутах)",
        "test_id": "Раздел теста",
        "is_exam": "Контрольная работа",
        "results_available_from": "Открыть результаты с",
        "created_on": "Дата создания",
        "created_by_id": "Автор",
        "meta": "Мета раздел",
    }

    column_formatters = {
        "created_by_id": created_by_formatter,
        "test_id": get_test_name,
    }

    form_extra_fields = {
        "is_exam": BooleanField(default=False),
        "results_available_from": DateTimeField(
            label="Дата открытия результатов",
            format="%d-%m-%Y %H:%M",
            description="Формат: d-m-Y, H:M. Время в мск. Обратите внимание, что без is_exam, ответы будут доступны в любом случае.",
        ),
        "test_id": QuerySelectField(
            "Раздел теста",
            query_factory=lambda: Test.query.filter(
                Test.created_by_id == current_user.id
            ).all(),
            get_pk=lambda test: test.id,
            get_label=lambda test: (
                test.name
                + (", " + test.description if test.description else "")
                + (" (" + User.query.get(test.created_by_id).nick)
                + ")"
                if test.created_by_id
                else ""
            ),
        ),
    }

    def on_model_change(self, form, model, is_created, **kwargs):
        super().on_model_change(form, model, is_created)

        model.test_id = model.test_id.get_id()

    pass


def get_section_name(view, context, model, name, **kwargs):
    if model.section_id is None:
        return "Без раздела"

    section = Section.query.get(model.section_id)
    if section and section.name:
        return section.name
    raise Exception("Error occurred while retrieving section name")


def get_question_type(view, context, model, name, **kwargs):
    types = {
        0: "Практическое задание",
        1: "С вариантами ответов",
        2: "На сортировку",
        3: "На сопоставление",
    }
    return types.get(model.question_type, "")


class QuestionView(MiminetAdminModelView):
    form_excluded_columns = MiminetAdminModelView.form_excluded_columns + [
        "practice_question",
        "session_questions",
        "created_by_user",
        "section",
    ]

    form_overrides = {
        "text": TextAreaField,
    }

    form_widget_args = {
        "text": {"rows": 4, "style": "font-family: monospace; width: 680px;"},
    }

    column_list = (
        "section_id",
        "text",
        "explanation",
        "question_type",
        "created_on",
        "created_by_id",
        "category_id",
    )
    column_sortable_list = ("created_on", "created_by_id", "section_id")

    column_labels = {
        "section_id": "Вопрос раздела",
        "created_on": "Дата создания",
        "explanation": "Пояснение",
        "created_by_id": "Автор",
        "question_type": "Тип вопроса",
        "text": "Текст вопроса",
        "category_id": "Категория",
    }

    column_formatters = {
        "created_by_id": created_by_formatter,  # type: ignore
        "section_id": get_section_name,  # type: ignore
        "question_type": get_question_type,  # type: ignore
        "text": lambda v, c, model, n, **kwargs: Markup.unescape(model.text),
    }

    form_extra_fields = {
        "section_id": QuerySelectField(
            "Вопрос раздела",
            query_factory=lambda: Section.query.filter(
                Section.created_by_id == current_user.id
            ).all(),
            get_pk=lambda section: section.id,
            get_label=lambda section: (
                section.name + (" (" + User.query.get(section.created_by_id).nick + ")")
                if section.created_by_id
                else ""
            ),
            allow_blank=True,
            blank_text="Без раздела",
        ),
        "question_type": SelectField(
            "Тип вопроса",
            choices=[
                (0, "Практическое задание"),
                (1, "С вариантами ответов"),
                (2, "На сортировку"),
                (3, "На сопоставление"),
            ],
            widget=Select2Widget(),
        ),
        "category_id": QuerySelectField(
            "Категория вопроса",
            query_factory=lambda: db.session.query(QuestionCategory),
            get_pk=lambda question_category: question_category.id,
            get_label=lambda question_category: question_category.name,
        ),
    }

    def on_model_change(self, form, model, is_created, **kwargs):
        super().on_model_change(form, model, is_created)

        if model.section_id:
            model.section_id = model.section_id.get_id()
        else:
            model.section_id = None

        model.category_id = model.category_id.get_id()
        model.text = Markup.escape(Markup.unescape(model.text))


def get_question_text(view, context, model, name, **kwargs):
    if not model.question_id:
        return "Вопрос не установлен"
    question = Question.query.get(model.question_id)
    return question.text if question and question.text else "Вопрос не найден"


class AnswerView(MiminetAdminModelView):
    column_list = (
        "question_id",
        "variant",
        "is_correct",
        "position",
        "left",
        "right",
        "created_by_id",
    )
    column_sortable_list = ("created_by_id", "question_id")

    column_labels = {
        "question_id": "Вопрос",
        "variant": "Вариант ответа",
        "position": "Позиция ответа",
        "left": "Левая часть",
        "right": "Правая часть",
        "created_by_id": "Автор",
    }

    column_formatters = {
        "question_id": get_question_text,
        "created_by_id": created_by_formatter,
    }

    form_extra_fields = {
        "question_id": QuerySelectField(
            "Вопрос",
            query_factory=lambda: Question.query.all(),
            get_pk=lambda question: question.id,
            get_label=lambda question: (
                question.text
                + (" (" + User.query.get(question.created_by_id).nick)
                + ")"
                if question.created_by_id
                else ""
            ),
        )
    }

    def on_model_change(self, form, model, is_created, **kwargs):
        # Call base class functionality
        super().on_model_change(form, model, is_created)

        model.question_id = str(model.question_id).removeprefix("<Question ")
        model.question_id = str(model.question_id).removesuffix(">")

        if model.variant:
            model.variant = Markup.escape(Markup.unescape(model.variant))

        if model.left:
            model.left = Markup.escape(Markup.unescape(model.left))

        if model.right:
            model.right = Markup.escape(Markup.unescape(model.right))

    pass


class QuestionCategoryView(MiminetAdminModelView):
    column_list = ("name",)

    column_labels = {
        "name": "Название",
    }

    pass


class CheckByQuestionForm(Form):
    question_id = SelectField("Вопрос", coerce=int)
    requirements = TextAreaField("Requirements JSON")


class SessionQuestionView(MiminetAdminModelView):
    list_template = "admin/sessionQuestionList.html"

    can_create = False
    can_delete = False

    column_list = (
        "id",
        "quiz_session_id",
        "question_id",
        "question_text",
        "is_correct",
        "score",
        "max_score",
    )

    column_labels = {
        "id": "ID записи",
        "quiz_session_id": "Сессия",
        "question_id": "Вопрос (ID)",
        "question_text": "Текст вопроса",
        "is_correct": "Ответ верный",
        "score": "Набрано баллов",
        "max_score": "Максимум",
    }

    @staticmethod
    def fmt_question_text(view, context, model, name):
        q = Question.query.get(model.question_id)
        return q.text if q else "<вопрос не найден>"

    column_formatters = {
        "question_text": fmt_question_text,
    }

    @expose("/")
    def index_view(self, **kwargs):
        return super().index_view(**kwargs)

    @action("check_by_question", "Проверить по вопросу", None)
    def action_dummy(self, ids):
        return redirect(url_for(".check_by_question_view"))

    @expose("/check-by-question/", methods=["GET", "POST"])
    def check_by_question_view(self, **kwargs):
        all_q = db.session.query(Question.id, Question.text).distinct().all()
        choices = [
            (q.id, q.text[:50] + "…" if len(q.text) > 50 else q.text) for q in all_q
        ]

        form = CheckByQuestionForm(request.form)
        form.question_id.choices = choices

        if request.method == "POST" and form.validate():
            try:
                requirements = json.loads(form.requirements.data)
            except json.JSONDecodeError:
                flash("Некорректный JSON в requirements.", "error")
                return self.render("admin/check_by_question.html", form=form)

            sq_entries = (
                db.session.query(SessionQuestion)
                .filter(
                    SessionQuestion.question_id == form.question_id.data,
                    SessionQuestion.max_score == 0,
                    SessionQuestion.quiz_session_id.isnot(None),
                )
                .all()
            )
            if not sq_entries:
                flash("Нет новых записей для этого вопроса.", "warning")
                return self.render("admin/check_by_question.html", form=form)

            for sq in sq_entries:
                nm = Network.query.filter_by(guid=sq.network_guid).first()
                if not nm:
                    flash(f"Сеть с GUID {sq.network_guid} не найдена.", "error")
                    continue

                raw_data = nm.network
                if isinstance(raw_data, dict):
                    network = raw_data
                else:
                    try:
                        network = json.loads(raw_data)
                    except json.JSONDecodeError:
                        flash(
                            f"Сеть для записи {sq.id} не может быть прочитана.", "error"
                        )
                        continue

                try:
                    create_check_task(network, requirements, sq.id)
                except Exception as e:
                    flash(f"Ошибка при проверке записи {sq.id}: {e}", "error")

            flash(
                f"Запросы на проверку отправлены для {len(sq_entries)} записей.",
                "success",
            )
            return redirect(url_for(".index_view"))

        return self.render("admin/check_by_question.html", form=form)


class CreateCheckTaskForm(Form):
    guids = TextAreaField("GUID-ы сетей (по одному на строку)")
    requirements = TextAreaField("Requirements (JSON)")
    submit = SubmitField("Создать задачу проверки")


class CreateCheckTaskView(MiminetAdminModelView):
    @expose("/", methods=["GET", "POST"])
    def index(self):
        form = CreateCheckTaskForm(request.form)
        if request.method == "POST" and form.validate():
            try:
                guids = [
                    line.strip()
                    for line in form.guids.data.strip().splitlines()
                    if line.strip()
                ]

                networks = []
                for guid in guids:
                    network = Network.query.filter(Network.guid == guid).first()
                    if not network:
                        raise ValueError(f"Сеть с GUID {guid} не найдена.")
                    networks.append((json.loads(network.network), guid))

                reqs = json.loads(form.requirements.data)
                create_check_task_json(networks, reqs)
                flash("Задача проверки успешно создана.", "success")
                return redirect(url_for(".index"))
            except Exception as e:
                flash(f"Ошибка: {str(e)}", "error")

        return self.render("admin/create_check_task.html", form=form)
