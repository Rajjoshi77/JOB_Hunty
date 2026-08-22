module.exports = {
  apps: [
    {
      name: "jobhunter-bot",
      script: "python",
      args: "-m app.main",
      cwd: "./",
      interpreter: "none",
      restart_delay: 5000,
      max_restarts: 50,
      autorestart: true,
      watch: false,
      env: {
        NODE_ENV: "production",
        PYTHONUNBUFFERED: "1"
      }
    }
  ]
};
