from pydantic import BaseModel, ConfigDict, Field, SecretStr, StrictBool


class PreferenceChanges(BaseModel):
    model_config = ConfigDict(extra="forbid")

class ReminderChanges(PreferenceChanges):
    period_reminder_enabled: StrictBool = False
    record_reminder_enabled: StrictBool = False


class RecordingChanges(PreferenceChanges):
    weekly_record_days_target: int | None = Field(default=None, ge=1, le=7, strict=True)
    show_focus: StrictBool = True
    show_summary: StrictBool = True
    show_questions: StrictBool = True


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: SecretStr = Field(min_length=1, max_length=72)
    new_password: SecretStr = Field(min_length=8, max_length=72)
