module.exports = {
  apps: [
    {
      name: "clipforge-backend",
      script: "app.py",
      interpreter: "python3",
      watch: false,
      env: {
        PYTHONDONTWRITEBYTECODE: "1",
      },
    },
  ],
};
