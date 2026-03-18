-- ============================================================
-- Nova AI Life Assistant — Language Learning Schema
-- ============================================================

-- Track overall progress for each language
CREATE TABLE IF NOT EXISTS user_learning_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    language TEXT NOT NULL,          -- e.g., 'Russian'
    current_level INTEGER DEFAULT 1,
    total_words_learned INTEGER DEFAULT 0,
    daily_streak INTEGER DEFAULT 0,
    last_lesson_at TIMESTAMPTZ,
    points INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, language)
);

-- Individual words/phrases the user is learning
CREATE TABLE IF NOT EXISTS vocabulary (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    language TEXT NOT NULL,
    word TEXT NOT NULL,
    translation TEXT NOT NULL,
    pronunciation TEXT,
    example_sentence TEXT,
    mastery_level INTEGER DEFAULT 0 CHECK (mastery_level BETWEEN 0 AND 100),
    next_review_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, language, word)
);

-- History of interactive lessons
CREATE TABLE IF NOT EXISTS learning_lessons (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    language TEXT NOT NULL,
    lesson_type TEXT,                -- 'chat', 'quiz', 'translation'
    content_summary TEXT,
    performance_score INTEGER,       -- 0 to 100
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE user_learning_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE vocabulary ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_lessons ENABLE ROW LEVEL SECURITY;

-- Policies
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'user_learning_progress' AND policyname = 'Users own learning progress') THEN
        CREATE POLICY "Users own learning progress" ON user_learning_progress FOR ALL USING (user_id = auth.uid());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'vocabulary' AND policyname = 'Users own vocabulary') THEN
        CREATE POLICY "Users own vocabulary" ON vocabulary FOR ALL USING (user_id = auth.uid());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'learning_lessons' AND policyname = 'Users own lessons') THEN
        CREATE POLICY "Users own lessons" ON learning_lessons FOR ALL USING (user_id = auth.uid());
    END IF;
END $$;
