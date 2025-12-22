class ClaudeCodeAnalytics < Formula
  include Language::Python::Virtualenv

  desc "Analytics platform for Claude Code conversations"
  homepage "https://github.com/sujankapadia/claude-code-utils"
  # Temporary: Using branch for local testing (replace with tag for release)
  url "https://github.com/sujankapadia/claude-code-utils/archive/refs/heads/feature/homebrew-packaging.tar.gz"
  sha256 :no_check  # Skip checksum for testing
  license "MIT"

  depends_on "python@3.11"
  depends_on "jq"

  # Python dependencies - will be generated with: brew update-python-resources claude-code-analytics
  # TODO: Generate these before release with:
  #   brew update-python-resources Formula/claude-code-analytics.rb
  #
  # Required resources: streamlit, pandas, altair, google-generativeai,
  #                     openai, jinja2, pyyaml, python-dotenv
  #
  # For now, testing without resources (will use system Python packages if available)

  def install
    # Create virtualenv and install Python dependencies
    virtualenv_install_with_resources

    # Install all files to libexec
    libexec.install Dir["*"]

    # Create wrapper scripts for CLI commands
    (bin/"claude-code-analytics").write <<~EOS
      #!/bin/bash
      cd "#{libexec}" && "#{libexec}/#{Formula["python@3.11"].opt_bin}/python3" -m streamlit run streamlit_app/app.py "$@"
    EOS

    (bin/"claude-code-import").write <<~EOS
      #!/bin/bash
      "#{libexec}/#{Formula["python@3.11"].opt_bin}/python3" "#{libexec}/scripts/import_conversations.py" "$@"
    EOS

    (bin/"claude-code-search").write <<~EOS
      #!/bin/bash
      "#{libexec}/#{Formula["python@3.11"].opt_bin}/python3" "#{libexec}/scripts/search_fts.py" "$@"
    EOS

    (bin/"claude-code-analyze").write <<~EOS
      #!/bin/bash
      "#{libexec}/#{Formula["python@3.11"].opt_bin}/python3" "#{libexec}/scripts/analyze_session.py" "$@"
    EOS

    chmod 0755, bin/"claude-code-analytics"
    chmod 0755, bin/"claude-code-import"
    chmod 0755, bin/"claude-code-search"
    chmod 0755, bin/"claude-code-analyze"
  end

  def post_install
    # Create required directories
    claude_scripts = Pathname.new(Dir.home) / ".claude" / "scripts"
    claude_scripts.mkpath

    # Copy hook scripts to ~/.claude/scripts/
    cp libexec/"hooks/export-conversation.sh", claude_scripts
    cp libexec/"scripts/pretty-print-transcript.py", claude_scripts
    chmod 0755, claude_scripts/"export-conversation.sh"
    chmod 0755, claude_scripts/"pretty-print-transcript.py"

    # Create config directory and .env file
    config_dir = Pathname.new(Dir.home) / ".config" / "claude-code-analytics"
    config_dir.mkpath

    unless (config_dir/".env").exist?
      cp libexec/".env.example", config_dir/".env"
    end

    # Configure Claude Code settings.json (if jq available)
    setup_claude_hooks if which("jq")
  end

  def setup_claude_hooks
    settings_file = Pathname.new(Dir.home) / ".claude" / "settings.json"
    hook_command = "bash ~/.claude/scripts/export-conversation.sh"

    if settings_file.exist?
      # Backup existing settings
      cp settings_file, "#{settings_file}.backup-#{Time.now.to_i}"

      # Check if hook already exists
      settings_content = File.read(settings_file)
      return if settings_content.include?(hook_command)

      # Add hook using jq
      system "jq",
             ". + {\"hooks\": (.hooks // {} | .SessionEnd = [{\"matcher\": \"\", \"hooks\": [{\"type\": \"command\", \"command\": \"#{hook_command}\"}]}])}",
             settings_file.to_s,
             out: "#{settings_file}.new"

      if File.exist?("#{settings_file}.new")
        mv "#{settings_file}.new", settings_file
      end
    else
      # Create new settings file with hook
      settings_file.write <<~JSON
        {
          "hooks": {
            "SessionEnd": [
              {
                "matcher": "",
                "hooks": [
                  {
                    "type": "command",
                    "command": "#{hook_command}"
                  }
                ]
              }
            ]
          }
        }
      JSON
    end
  end

  def caveats
    <<~EOS
      Claude Code Analytics has been installed!

      ⚠️  REQUIREMENT: This tool analyzes Claude Code conversations.
      If you haven't installed Claude Code yet:

        brew install --cask claude-code

      The analytics tool processes exported conversation data and works
      independently - Claude Code doesn't need to be running.

      🎯 Quick Start:
        1. Launch the dashboard:
           $ claude-code-analytics

        2. The dashboard will open at http://localhost:8501

        3. Click "Run Import" to import your conversations

      ⚙️  Configuration:
        Edit ~/.config/claude-code-analytics/.env to customize settings

      🔑 For AI analysis features, add an API key:
        export OPENROUTER_API_KEY="sk-or-your-key"
        # or
        export GOOGLE_API_KEY="your-key"

      📦 CLI Commands:
        claude-code-analytics    # Launch dashboard
        claude-code-import       # Import conversations
        claude-code-search       # Search conversations
        claude-code-analyze      # Analyze sessions

      📚 Documentation:
        https://github.com/sujankapadia/claude-code-utils

      🪝 SessionEnd Hook:
        The hook has been automatically installed to:
        ~/.claude/settings.json

        Conversations will be exported automatically to:
        ~/claude-conversations/
    EOS
  end

  test do
    # Create test environment
    testpath_conversations = testpath/"claude-conversations"
    testpath_conversations.mkpath

    testpath_projects = testpath/".claude"/"projects"
    testpath_projects.mkpath

    testpath_project = testpath_projects/"test-project"
    testpath_project.mkpath

    # Create a minimal test transcript
    test_transcript = testpath_project/"session-test.jsonl"
    test_transcript.write <<~JSONL
      {"type":"conversation_metadata","session_id":"test-session-123","started_at":"2024-01-01T00:00:00Z"}
      {"type":"message","message":{"role":"user","content":"Hello, test message","timestamp":"2024-01-01T00:00:01Z"}}
      {"type":"message","message":{"role":"assistant","content":"Hello! This is a test response.","timestamp":"2024-01-01T00:00:02Z"}}
    JSONL

    # Set environment variables to use testpath
    ENV["CLAUDE_CONVERSATIONS_DIR"] = testpath_conversations.to_s
    ENV["CLAUDE_CODE_PROJECTS_DIR"] = testpath_projects.to_s
    ENV["DATABASE_PATH"] = "#{testpath_conversations}/conversations.db"

    # Test 1: Import should create database and import data
    system bin/"claude-code-import"
    assert_predicate testpath_conversations/"conversations.db", :exist?, "Database should be created"

    # Test 2: Verify database has correct structure
    output = shell_output("sqlite3 #{testpath_conversations}/conversations.db 'SELECT name FROM sqlite_master WHERE type=\"table\" ORDER BY name'")
    assert_match "messages", output, "Database should have messages table"
    assert_match "sessions", output, "Database should have sessions table"
    assert_match "projects", output, "Database should have projects table"
    assert_match "tool_uses", output, "Database should have tool_uses table"

    # Test 3: Verify data was imported
    messages_count = shell_output("sqlite3 #{testpath_conversations}/conversations.db 'SELECT COUNT(*) FROM messages'").strip
    assert_equal "2", messages_count, "Should have imported 2 messages"

    # Test 4: Verify FTS tables were created
    output = shell_output("sqlite3 #{testpath_conversations}/conversations.db 'SELECT name FROM sqlite_master WHERE type=\"table\" AND name LIKE \"fts_%\"'")
    assert_match "fts_messages", output, "FTS search index should be created"

    # Test 5: Test search functionality
    system bin/"claude-code-search", "test", "--output-mode=count"

    # Test 6: Verify CLI commands have proper help
    assert_match "usage", shell_output("#{bin}/claude-code-import --help")
    assert_match "usage", shell_output("#{bin}/claude-code-search --help")
    assert_match "usage", shell_output("#{bin}/claude-code-analyze --help")
  end
end
