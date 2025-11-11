# Archon Advanced UI - Quick Reference Card

## Navigation

Access from sidebar:
- **Analytics** → Metrics, charts, and data tables
- **Knowledge Graph** → Interactive graph visualization
- **Scheduler** → Calendar, Gantt chart, auto-scheduling

---

## Analytics Dashboard

### Quick Actions
1. **View Metrics**: Top of page shows 5 key metrics
2. **Explore Charts**: 6 interactive Plotly charts
3. **Review Tables**: 4 data tables with insights
4. **Export Data**: CSV downloads for projects, tasks, knowledge

### Filters
- Date Range: Select start and end dates
- Project: Filter by specific project
- Status: Filter by status (planning, in_progress, etc.)

### Key Charts
- **Project Status**: Pie chart of project distribution
- **Task Status**: Bar chart of task distribution
- **Coverage**: Histogram of knowledge coverage scores
- **Priority**: Bar chart of tasks by priority
- **Agent Types**: Pie chart of task assignments
- **Timeline**: Projects/tasks created over time

---

## Knowledge Graph

### Quick Actions
1. **Filter**: Use sidebar to filter by framework, type, or tag
2. **Search**: Search by title or tag (results highlighted in pink)
3. **Select Node**: Choose from dropdown to view details
4. **Find Path**: Use path finder to connect two nodes

### Controls
- **Layout**: Choose spring, circular, or kamada_kawai
- **Show Task Relationships**: Toggle to see task connections
- **Refresh**: Reload graph with current filters

### Node Colors
- **Framework colors**: FastAPI (green), React (blue), etc.
- **Gold**: Selected node
- **Pink**: Search results

### Edge Colors
- **Red**: Prerequisites
- **Blue**: Related content
- **Green**: Examples
- **Orange**: Extensions
- **Purple**: Shared tasks

---

## Scheduler

### Quick Actions
1. **View Calendar**: Monthly view with task indicators
2. **Check Gantt**: Timeline view with dependencies
3. **Auto-Schedule**: Intelligent scheduling based on dependencies
4. **Review Capacity**: Agent workload visualization

### Auto-Schedule Steps
1. Set project start date
2. Set working hours per day (1-24)
3. Click "Auto-Schedule All Tasks"
4. Review preview
5. Schedule updates in database

### Views
- **Calendar**: Monthly view with colored task dots
- **Gantt**: Timeline bars (red = critical path)
- **Agent Capacity**: Stacked bar chart by agent
- **Quick Stats**: Metrics at bottom

### Critical Path
- Automatically calculated
- Highlighted in red on Gantt chart
- Shows longest dependency chain

---

## Common Workflows

### 1. Analyze Project Health
```
Analytics → Select project → Review metrics → Check coverage
```

### 2. Find Knowledge Gaps
```
Analytics → Bottom 5 Coverage table → Note low tasks
Knowledge Graph → Search topics → Attach knowledge
```

### 3. Schedule New Project
```
Projects → Create project → Tasks → Add tasks & dependencies
Scheduler → Auto-Schedule → Review Gantt
```

### 4. Explore Knowledge
```
Knowledge Graph → Filter by framework → Select nodes → View details
Path Finder → Find connections
```

### 5. Balance Workload
```
Scheduler → Agent Capacity view → Review distribution
Tasks → Reassign overloaded agents
```

### 6. Track Progress
```
Analytics → Timeline chart → Review activity
Recent Activity table → See latest updates
```

---

## Keyboard Shortcuts

(Streamlit default shortcuts)
- **R**: Rerun the app
- **C**: Clear cache
- **?**: Show keyboard shortcuts

---

## Tips & Tricks

### Analytics
- Use date range to focus on specific time periods
- Export CSV for offline analysis or reporting
- Check "Bottom 5 Coverage" regularly to identify gaps

### Knowledge Graph
- Start with framework filter to reduce node count
- Use search to quickly find specific topics
- Path finder helps understand knowledge flow
- Most connected nodes are usually core concepts

### Scheduler
- Run auto-schedule early to identify timeline issues
- Critical path shows where delays will impact deadline
- Agent capacity view helps prevent overload
- Update estimates regularly for better scheduling

---

## Color Legend

### Status Colors
- **Gray** (#808080): Pending/Unknown
- **Blue** (#4B9EFF): Ready/In Progress
- **Orange** (#FFA500): In Progress/Warning
- **Red** (#FF4B4B): Blocked/High Priority
- **Green** (#00CC99): Completed/Success
- **Gold** (#FFD700): On Hold/Selected

### Priority Colors
- **Priority 1** (Highest): Red
- **Priority 2**: Orange
- **Priority 3**: Yellow
- **Priority 4**: Light Green
- **Priority 5** (Lowest): Green

---

## File Locations

```
/home/user/Archon/streamlit_pages/
├── analytics.py          # Analytics dashboard
├── knowledge_graph.py    # Graph visualization
└── scheduler.py          # Task scheduler
```

---

## Database Tables Used

- **projects**: Project data
- **tasks**: Task data
- **knowledge**: Knowledge chunks
- **task_knowledge_links**: Task-knowledge relationships
- **task_dependencies**: Task dependencies
- **knowledge_relationships**: Knowledge relationships

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No data showing | Check Supabase connection in Database tab |
| Graph not rendering | Verify knowledge chunks exist, try different layout |
| Auto-schedule fails | Check task durations and dependencies |
| Charts empty | Ensure data exists for selected filters |
| Performance slow | Reduce date range or use more specific filters |

---

## Performance Limits

- **Knowledge Graph**: 500 nodes max
- **Analytics**: All data (use filters for large datasets)
- **Scheduler**: All tasks (consider project filter)

---

## Need Help?

1. Check **ADVANCED_UI_FEATURES_GUIDE.md** for detailed documentation
2. Review error messages in Streamlit UI
3. Check browser console for JavaScript errors
4. Verify database connection in Database tab

---

**Quick Start**: Click "Analytics" → See metrics → Click "Knowledge Graph" → Explore knowledge → Click "Scheduler" → Auto-schedule tasks!

**Pro Tip**: Use all three pages together for comprehensive project management: Analytics for insights, Knowledge Graph for exploration, Scheduler for planning.
