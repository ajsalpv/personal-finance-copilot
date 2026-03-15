-- ============================================================
-- CHAT MESSAGES (Persistence)
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'bot')),
    text TEXT NOT NULL,
    thread_id TEXT,
    memory_recalled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages(user_id, created_at DESC);
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Users own chat messages') THEN
        CREATE POLICY "Users own chat messages" ON chat_messages FOR ALL USING (user_id = auth.uid());
    END IF;
END $$;
