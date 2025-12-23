"""Pydantic models for Google Tasks API responses."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskLink(BaseModel):
    """Google Tasks link model."""

    model_config = ConfigDict(populate_by_name=True)

    description: str | None = None
    link: str


class Task(BaseModel):
    """Google Tasks task model.

    Represents a single task with all associated metadata, due dates,
    links, and relationships to task lists.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str | None = None
    title: str
    description: str | None = None
    status: str | None = None  # needsAction, completed
    due: str | None = None  # Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS.fffZ (RFC 3339)
    completed: datetime | None = None
    notes: str | None = None
    parent: str | None = None  # Parent task ID (for subtasks)
    position: str | None = None  # Relative position in task list (used for ordering)
    links: list[TaskLink] | None = None
    updated: datetime | None = None
    deleted: bool = False
    hidden: bool = False
    web_view_link: str | None = Field(default=None, alias="webViewLink")
    etag: str | None = None
    kind: str | None = None  # Always "tasks#task"

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate task title is not empty and within length limits."""
        if not v or not v.strip():
            raise ValueError("Task title cannot be empty")
        if len(v) > 1024:
            raise ValueError("Task title cannot exceed 1024 characters")
        return v.strip()


class TaskCreate(BaseModel):
    """Model for creating a new task.

    Contains only the fields that can be set during task creation.
    """

    model_config = ConfigDict(populate_by_name=True)

    title: str
    description: str | None = None
    due: str | None = None  # YYYY-MM-DD format
    notes: str | None = None
    parent: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate task title is not empty and within length limits."""
        if not v or not v.strip():
            raise ValueError("Task title cannot be empty")
        if len(v) > 1024:
            raise ValueError("Task title cannot exceed 1024 characters")
        return v.strip()


class TaskUpdate(BaseModel):
    """Model for updating an existing task.

    All fields are optional to allow partial updates.
    """

    model_config = ConfigDict(populate_by_name=True)

    title: str | None = None
    description: str | None = None
    due: str | None = None
    notes: str | None = None
    status: str | None = None  # needsAction, completed

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        """Validate task title if provided."""
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Task title cannot be empty")
        if len(v) > 1024:
            raise ValueError("Task title cannot exceed 1024 characters")
        return v.strip()


class TaskList(BaseModel):
    """Google Tasks task list model.

    Represents a task list that contains multiple tasks.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    updated: datetime | None = None
    etag: str | None = None
    kind: str | None = None  # Always "tasks#taskList"
    self_link: str | None = Field(default=None, alias="selfLink")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate task list title is not empty."""
        if not v or not v.strip():
            raise ValueError("Task list title cannot be empty")
        return v.strip()


class TaskListCreate(BaseModel):
    """Model for creating a new task list."""

    model_config = ConfigDict(populate_by_name=True)

    title: str

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate task list title is not empty."""
        if not v or not v.strip():
            raise ValueError("Task list title cannot be empty")
        return v.strip()


class TasksListResponse(BaseModel):
    """Response model for listing tasks in a task list."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[Task] = Field(default_factory=list)
    next_page_token: str | None = Field(default=None, alias="nextPageToken")
    etag: str | None = None
    kind: str | None = None  # Always "tasks#tasks"


class TaskListsResponse(BaseModel):
    """Response model for listing task lists."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[TaskList] = Field(default_factory=list)
    next_page_token: str | None = Field(default=None, alias="nextPageToken")
    etag: str | None = None
    kind: str | None = None  # Always "tasks#taskLists"
