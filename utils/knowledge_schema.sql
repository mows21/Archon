-- ============================================================================
-- ARCHON KNOWLEDGE MANAGEMENT SCHEMA
-- Enhanced database schema for knowledge-aware project and task management
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- PART 1: ENHANCE EXISTING site_pages TABLE
-- ============================================================================

-- Add new columns to existing site_pages table for enhanced knowledge management
-- Run these one at a time if table already exists, or skip if creating fresh

ALTER TABLE site_pages
ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS knowledge_type TEXT DEFAULT 'documentation',
ADD COLUMN IF NOT EXISTS framework TEXT,
ADD COLUMN IF NOT EXISTS language TEXT,
ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now());

-- Add check constraint for knowledge_type
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'site_pages_knowledge_type_check'
    ) THEN
        ALTER TABLE site_pages
        ADD CONSTRAINT site_pages_knowledge_type_check
        CHECK (knowledge_type IN ('documentation', 'tutorial', 'api_reference', 'example', 'blog', 'learned_insight', 'other'));
    END IF;
END $$;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_site_pages_tags ON site_pages USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_site_pages_knowledge_type ON site_pages (knowledge_type);
CREATE INDEX IF NOT EXISTS idx_site_pages_framework ON site_pages (framework);
CREATE INDEX IF NOT EXISTS idx_site_pages_language ON site_pages (language);

-- Add comment
COMMENT ON TABLE site_pages IS 'Stores chunked documentation and knowledge with vector embeddings for RAG';

-- ============================================================================
-- PART 2: KNOWLEDGE SOURCES TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS knowledge_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_url TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'documentation',
    framework TEXT,
    language TEXT,
    crawl_config JSONB DEFAULT '{}'::jsonb,

    -- Tracking
    last_crawled TIMESTAMP WITH TIME ZONE,
    crawl_frequency TEXT DEFAULT 'on-demand', -- 'daily', 'weekly', 'monthly', 'on-demand'
    next_crawl_scheduled TIMESTAMP WITH TIME ZONE,
    crawl_status TEXT DEFAULT 'pending', -- 'pending', 'in-progress', 'completed', 'failed'

    -- Stats
    total_pages_crawled INTEGER DEFAULT 0,
    total_chunks_created INTEGER DEFAULT 0,
    last_crawl_duration_seconds INTEGER,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),

    CONSTRAINT knowledge_sources_source_type_check
        CHECK (source_type IN ('documentation', 'github', 'tutorial', 'blog', 'api', 'other')),
    CONSTRAINT knowledge_sources_crawl_frequency_check
        CHECK (crawl_frequency IN ('daily', 'weekly', 'monthly', 'on-demand')),
    CONSTRAINT knowledge_sources_crawl_status_check
        CHECK (crawl_status IN ('pending', 'in-progress', 'completed', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_knowledge_sources_framework ON knowledge_sources (framework);
CREATE INDEX IF NOT EXISTS idx_knowledge_sources_crawl_status ON knowledge_sources (crawl_status);
CREATE INDEX IF NOT EXISTS idx_knowledge_sources_next_crawl ON knowledge_sources (next_crawl_scheduled);

COMMENT ON TABLE knowledge_sources IS 'Tracks external knowledge sources and their crawl schedules';

-- ============================================================================
-- PART 3: PROJECTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'planning',
    priority INTEGER DEFAULT 3, -- 1 (highest) to 5 (lowest)

    -- Scheduling
    deadline TIMESTAMP WITH TIME ZONE,
    estimated_duration_minutes INTEGER,
    actual_duration_minutes INTEGER,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Knowledge integration
    required_knowledge_tags TEXT[] DEFAULT '{}',
    required_frameworks TEXT[] DEFAULT '{}',
    knowledge_context_embedding VECTOR(1536), -- Embedding of project description
    attached_knowledge_ids BIGINT[] DEFAULT '{}', -- References to site_pages.id
    knowledge_coverage_score FLOAT, -- 0-1, how much required knowledge is available

    -- Auto-scheduling hints
    can_auto_schedule BOOLEAN DEFAULT true,
    scheduling_constraints JSONB DEFAULT '{}'::jsonb,

    -- Metadata
    created_by TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),

    CONSTRAINT projects_status_check
        CHECK (status IN ('planning', 'ready', 'in_progress', 'blocked', 'completed', 'cancelled', 'on_hold')),
    CONSTRAINT projects_priority_check
        CHECK (priority BETWEEN 1 AND 5),
    CONSTRAINT projects_knowledge_coverage_check
        CHECK (knowledge_coverage_score IS NULL OR (knowledge_coverage_score >= 0 AND knowledge_coverage_score <= 1))
);

CREATE INDEX IF NOT EXISTS idx_projects_status ON projects (status);
CREATE INDEX IF NOT EXISTS idx_projects_priority ON projects (priority);
CREATE INDEX IF NOT EXISTS idx_projects_deadline ON projects (deadline);
CREATE INDEX IF NOT EXISTS idx_projects_tags ON projects USING GIN (required_knowledge_tags);
CREATE INDEX IF NOT EXISTS idx_projects_frameworks ON projects USING GIN (required_frameworks);
CREATE INDEX IF NOT EXISTS idx_projects_knowledge_embedding ON projects USING ivfflat (knowledge_context_embedding vector_cosine_ops);

COMMENT ON TABLE projects IS 'Projects with knowledge context and auto-scheduling capabilities';

-- ============================================================================
-- PART 4: TASKS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    parent_task_id UUID REFERENCES tasks(id) ON DELETE CASCADE, -- For subtasks

    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 3, -- 1 (highest) to 5 (lowest)

    -- Scheduling
    deadline TIMESTAMP WITH TIME ZONE,
    estimated_duration_minutes INTEGER,
    actual_duration_minutes INTEGER,
    scheduled_start TIMESTAMP WITH TIME ZONE,
    scheduled_end TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Knowledge integration
    required_knowledge_tags TEXT[] DEFAULT '{}',
    required_frameworks TEXT[] DEFAULT '{}',
    task_context_embedding VECTOR(1536), -- Embedding of task description
    attached_knowledge_ids BIGINT[] DEFAULT '{}', -- References to site_pages.id
    learned_knowledge_ids BIGINT[] DEFAULT '{}', -- Knowledge created during task execution
    knowledge_coverage_score FLOAT, -- 0-1, how much required knowledge is available

    -- Agent assignment
    assigned_agent_type TEXT, -- 'coder', 'scraper', 'refiner', 'custom'
    assigned_agent_name TEXT, -- Specific agent instance
    agent_config JSONB DEFAULT '{}'::jsonb, -- Configuration for the agent
    execution_result JSONB, -- Result from agent execution

    -- Blocking and dependencies (simplified - detailed dependencies in separate table)
    is_blocked BOOLEAN DEFAULT false,
    blocker_reason TEXT,

    -- Metadata
    created_by TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),

    CONSTRAINT tasks_status_check
        CHECK (status IN ('pending', 'ready', 'in_progress', 'blocked', 'completed', 'cancelled', 'failed')),
    CONSTRAINT tasks_priority_check
        CHECK (priority BETWEEN 1 AND 5),
    CONSTRAINT tasks_knowledge_coverage_check
        CHECK (knowledge_coverage_score IS NULL OR (knowledge_coverage_score >= 0 AND knowledge_coverage_score <= 1))
);

CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks (project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_parent_task_id ON tasks (parent_task_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks (priority);
CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks (deadline);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_agent ON tasks (assigned_agent_type);
CREATE INDEX IF NOT EXISTS idx_tasks_tags ON tasks USING GIN (required_knowledge_tags);
CREATE INDEX IF NOT EXISTS idx_tasks_frameworks ON tasks USING GIN (required_frameworks);
CREATE INDEX IF NOT EXISTS idx_tasks_is_blocked ON tasks (is_blocked);
CREATE INDEX IF NOT EXISTS idx_tasks_knowledge_embedding ON tasks USING ivfflat (task_context_embedding vector_cosine_ops);

COMMENT ON TABLE tasks IS 'Tasks with knowledge attachment and agent assignment';

-- ============================================================================
-- PART 5: TASK DEPENDENCIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS task_dependencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    depends_on_task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    dependency_type TEXT DEFAULT 'finish_to_start',
    lag_minutes INTEGER DEFAULT 0, -- Time gap between tasks (can be negative for lead time)

    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),

    CONSTRAINT task_dependencies_type_check
        CHECK (dependency_type IN ('finish_to_start', 'start_to_start', 'finish_to_finish', 'start_to_finish')),
    CONSTRAINT task_dependencies_no_self_reference
        CHECK (task_id != depends_on_task_id),
    UNIQUE(task_id, depends_on_task_id)
);

CREATE INDEX IF NOT EXISTS idx_task_dependencies_task_id ON task_dependencies (task_id);
CREATE INDEX IF NOT EXISTS idx_task_dependencies_depends_on ON task_dependencies (depends_on_task_id);

COMMENT ON TABLE task_dependencies IS 'Defines dependencies between tasks for scheduling';

-- ============================================================================
-- PART 6: TASK-KNOWLEDGE LINKS (Many-to-Many)
-- ============================================================================

CREATE TABLE IF NOT EXISTS task_knowledge_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    knowledge_id BIGINT NOT NULL REFERENCES site_pages(id) ON DELETE CASCADE,

    relevance_score FLOAT DEFAULT 0.0, -- 0-1, how relevant this knowledge is
    link_type TEXT DEFAULT 'suggested',

    -- Who/what created this link
    linked_by TEXT, -- 'auto', 'user', 'agent_name'
    link_reason TEXT, -- Why was this linked

    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),

    CONSTRAINT task_knowledge_links_relevance_check
        CHECK (relevance_score >= 0 AND relevance_score <= 1),
    CONSTRAINT task_knowledge_links_type_check
        CHECK (link_type IN ('required', 'suggested', 'learned', 'reference')),
    UNIQUE(task_id, knowledge_id)
);

CREATE INDEX IF NOT EXISTS idx_task_knowledge_links_task_id ON task_knowledge_links (task_id);
CREATE INDEX IF NOT EXISTS idx_task_knowledge_links_knowledge_id ON task_knowledge_links (knowledge_id);
CREATE INDEX IF NOT EXISTS idx_task_knowledge_links_relevance ON task_knowledge_links (relevance_score DESC);
CREATE INDEX IF NOT EXISTS idx_task_knowledge_links_type ON task_knowledge_links (link_type);

COMMENT ON TABLE task_knowledge_links IS 'Links tasks to relevant knowledge chunks with relevance scores';

-- ============================================================================
-- PART 7: KNOWLEDGE RELATIONSHIPS (Knowledge Graph)
-- ============================================================================

CREATE TABLE IF NOT EXISTS knowledge_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_knowledge_id BIGINT NOT NULL REFERENCES site_pages(id) ON DELETE CASCADE,
    to_knowledge_id BIGINT NOT NULL REFERENCES site_pages(id) ON DELETE CASCADE,

    relationship_type TEXT NOT NULL,
    confidence FLOAT DEFAULT 0.0, -- 0-1

    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),

    CONSTRAINT knowledge_relationships_type_check
        CHECK (relationship_type IN ('depends_on', 'related_to', 'example_of', 'prerequisite_for', 'alternative_to', 'extends')),
    CONSTRAINT knowledge_relationships_confidence_check
        CHECK (confidence >= 0 AND confidence <= 1),
    CONSTRAINT knowledge_relationships_no_self_reference
        CHECK (from_knowledge_id != to_knowledge_id),
    UNIQUE(from_knowledge_id, to_knowledge_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_relationships_from ON knowledge_relationships (from_knowledge_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_relationships_to ON knowledge_relationships (to_knowledge_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_relationships_type ON knowledge_relationships (relationship_type);

COMMENT ON TABLE knowledge_relationships IS 'Defines relationships between knowledge chunks for knowledge graph';

-- ============================================================================
-- PART 8: AGENT SCHEDULES (Tracking agent task execution)
-- ============================================================================

CREATE TABLE IF NOT EXISTS agent_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,

    scheduled_start TIMESTAMP WITH TIME ZONE,
    scheduled_end TIMESTAMP WITH TIME ZONE,
    actual_start TIMESTAMP WITH TIME ZONE,
    actual_end TIMESTAMP WITH TIME ZONE,

    status TEXT DEFAULT 'scheduled',
    result JSONB,
    error_message TEXT,

    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),

    CONSTRAINT agent_schedules_status_check
        CHECK (status IN ('scheduled', 'running', 'completed', 'failed', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_agent_schedules_agent_name ON agent_schedules (agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_schedules_task_id ON agent_schedules (task_id);
CREATE INDEX IF NOT EXISTS idx_agent_schedules_status ON agent_schedules (status);
CREATE INDEX IF NOT EXISTS idx_agent_schedules_scheduled_start ON agent_schedules (scheduled_start);

COMMENT ON TABLE agent_schedules IS 'Tracks agent task execution schedules and results';

-- ============================================================================
-- PART 9: ENHANCED RPC FUNCTIONS
-- ============================================================================

-- Enhanced function to search knowledge with advanced filtering
CREATE OR REPLACE FUNCTION match_knowledge_advanced (
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 10,
    match_threshold FLOAT DEFAULT 0.0,
    required_tags TEXT[] DEFAULT '{}',
    required_frameworks TEXT[] DEFAULT '{}',
    knowledge_types TEXT[] DEFAULT '{}',
    language_filter TEXT DEFAULT NULL
) RETURNS TABLE (
    id BIGINT,
    url VARCHAR,
    chunk_number INTEGER,
    title VARCHAR,
    summary VARCHAR,
    content TEXT,
    tags TEXT[],
    knowledge_type TEXT,
    framework TEXT,
    language TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        sp.id,
        sp.url,
        sp.chunk_number,
        sp.title,
        sp.summary,
        sp.content,
        sp.tags,
        sp.knowledge_type,
        sp.framework,
        sp.language,
        sp.metadata,
        1 - (sp.embedding <=> query_embedding) AS similarity
    FROM site_pages sp
    WHERE
        (1 - (sp.embedding <=> query_embedding)) >= match_threshold
        AND (cardinality(required_tags) = 0 OR sp.tags && required_tags)
        AND (cardinality(required_frameworks) = 0 OR sp.framework = ANY(required_frameworks))
        AND (cardinality(knowledge_types) = 0 OR sp.knowledge_type = ANY(knowledge_types))
        AND (language_filter IS NULL OR sp.language = language_filter)
    ORDER BY sp.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION match_knowledge_advanced IS 'Advanced knowledge search with multiple filters';

-- Function to get all knowledge for a specific task
CREATE OR REPLACE FUNCTION get_task_knowledge (
    task_id_param UUID
) RETURNS TABLE (
    id BIGINT,
    url VARCHAR,
    title VARCHAR,
    summary VARCHAR,
    content TEXT,
    tags TEXT[],
    knowledge_type TEXT,
    framework TEXT,
    relevance_score FLOAT,
    link_type TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        sp.id,
        sp.url,
        sp.title,
        sp.summary,
        sp.content,
        sp.tags,
        sp.knowledge_type,
        sp.framework,
        tkl.relevance_score,
        tkl.link_type
    FROM site_pages sp
    INNER JOIN task_knowledge_links tkl ON sp.id = tkl.knowledge_id
    WHERE tkl.task_id = task_id_param
    ORDER BY tkl.relevance_score DESC;
END;
$$;

COMMENT ON FUNCTION get_task_knowledge IS 'Retrieves all knowledge chunks linked to a specific task';

-- Function to get task dependencies with details
CREATE OR REPLACE FUNCTION get_task_dependencies_tree (
    task_id_param UUID
) RETURNS TABLE (
    dependency_id UUID,
    task_id UUID,
    task_name TEXT,
    task_status TEXT,
    depends_on_task_id UUID,
    depends_on_task_name TEXT,
    depends_on_task_status TEXT,
    dependency_type TEXT,
    lag_minutes INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        td.id AS dependency_id,
        t1.id AS task_id,
        t1.name AS task_name,
        t1.status AS task_status,
        t2.id AS depends_on_task_id,
        t2.name AS depends_on_task_name,
        t2.status AS depends_on_task_status,
        td.dependency_type,
        td.lag_minutes
    FROM task_dependencies td
    INNER JOIN tasks t1 ON td.task_id = t1.id
    INNER JOIN tasks t2 ON td.depends_on_task_id = t2.id
    WHERE td.task_id = task_id_param;
END;
$$;

COMMENT ON FUNCTION get_task_dependencies_tree IS 'Gets all dependencies for a task with full details';

-- Function to check if knowledge exists for given tags
CREATE OR REPLACE FUNCTION check_knowledge_coverage (
    required_tags_param TEXT[],
    required_frameworks_param TEXT[] DEFAULT '{}'
) RETURNS TABLE (
    total_chunks INTEGER,
    coverage_score FLOAT,
    missing_tags TEXT[],
    available_frameworks TEXT[]
)
LANGUAGE plpgsql
AS $$
DECLARE
    total_count INTEGER;
    coverage FLOAT;
    missing TEXT[];
    available TEXT[];
BEGIN
    -- Count matching chunks
    SELECT COUNT(*)
    INTO total_count
    FROM site_pages
    WHERE tags && required_tags_param
    AND (cardinality(required_frameworks_param) = 0 OR framework = ANY(required_frameworks_param));

    -- Calculate coverage (simple heuristic)
    coverage := LEAST(1.0, total_count::FLOAT / GREATEST(1, cardinality(required_tags_param) * 5));

    -- Find missing tags (tags with < 3 chunks)
    SELECT ARRAY_AGG(tag)
    INTO missing
    FROM unnest(required_tags_param) AS tag
    WHERE NOT EXISTS (
        SELECT 1
        FROM site_pages
        WHERE tag = ANY(tags)
        HAVING COUNT(*) >= 3
    );

    -- Get available frameworks
    SELECT ARRAY_AGG(DISTINCT framework)
    INTO available
    FROM site_pages
    WHERE tags && required_tags_param
    AND framework IS NOT NULL;

    RETURN QUERY SELECT total_count, coverage, COALESCE(missing, '{}'), COALESCE(available, '{}');
END;
$$;

COMMENT ON FUNCTION check_knowledge_coverage IS 'Checks how much knowledge is available for given tags and frameworks';

-- ============================================================================
-- PART 10: ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Enable RLS on all new tables
ALTER TABLE knowledge_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_dependencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_knowledge_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_schedules ENABLE ROW LEVEL SECURITY;

-- Create public read/write policies (adjust based on your security needs)
CREATE POLICY "Allow public read access" ON knowledge_sources FOR SELECT TO public USING (true);
CREATE POLICY "Allow public write access" ON knowledge_sources FOR INSERT TO public WITH CHECK (true);
CREATE POLICY "Allow public update access" ON knowledge_sources FOR UPDATE TO public USING (true);

CREATE POLICY "Allow public read access" ON projects FOR SELECT TO public USING (true);
CREATE POLICY "Allow public write access" ON projects FOR INSERT TO public WITH CHECK (true);
CREATE POLICY "Allow public update access" ON projects FOR UPDATE TO public USING (true);

CREATE POLICY "Allow public read access" ON tasks FOR SELECT TO public USING (true);
CREATE POLICY "Allow public write access" ON tasks FOR INSERT TO public WITH CHECK (true);
CREATE POLICY "Allow public update access" ON tasks FOR UPDATE TO public USING (true);

CREATE POLICY "Allow public read access" ON task_dependencies FOR SELECT TO public USING (true);
CREATE POLICY "Allow public write access" ON task_dependencies FOR INSERT TO public WITH CHECK (true);

CREATE POLICY "Allow public read access" ON task_knowledge_links FOR SELECT TO public USING (true);
CREATE POLICY "Allow public write access" ON task_knowledge_links FOR INSERT TO public WITH CHECK (true);

CREATE POLICY "Allow public read access" ON knowledge_relationships FOR SELECT TO public USING (true);
CREATE POLICY "Allow public write access" ON knowledge_relationships FOR INSERT TO public WITH CHECK (true);

CREATE POLICY "Allow public read access" ON agent_schedules FOR SELECT TO public USING (true);
CREATE POLICY "Allow public write access" ON agent_schedules FOR INSERT TO public WITH CHECK (true);
CREATE POLICY "Allow public update access" ON agent_schedules FOR UPDATE TO public USING (true);

-- ============================================================================
-- PART 11: TRIGGERS FOR AUTOMATIC UPDATES
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
CREATE TRIGGER update_knowledge_sources_updated_at BEFORE UPDATE ON knowledge_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Uncomment these to verify the schema was created successfully:

-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public'
-- AND table_name IN ('site_pages', 'knowledge_sources', 'projects', 'tasks',
--                    'task_dependencies', 'task_knowledge_links',
--                    'knowledge_relationships', 'agent_schedules')
-- ORDER BY table_name;

-- SELECT routine_name FROM information_schema.routines
-- WHERE routine_schema = 'public'
-- AND routine_type = 'FUNCTION'
-- AND routine_name IN ('match_knowledge_advanced', 'get_task_knowledge',
--                      'get_task_dependencies_tree', 'check_knowledge_coverage')
-- ORDER BY routine_name;
