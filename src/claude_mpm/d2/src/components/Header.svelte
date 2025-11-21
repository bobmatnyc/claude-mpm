<script>
  let { statusText, statusColor, port } = $props();
</script>

<header class="header">
  <div class="header-content">
    <div class="title">
      <h1>Claude MPM Dashboard</h1>
      <span class="version">v2.0</span>
    </div>

    <div class="connection-status">
      <div class="status-indicator" style="background: {statusColor}"></div>
      <span class="status-text">{statusText}</span>
      <span class="port">:{port}</span>
    </div>
  </div>
</header>

<style>
  .header {
    height: 60px;
    background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
    border-bottom: 1px solid #333;
    display: flex;
    align-items: center;
    padding: 0 24px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  }

  .header-content {
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .title {
    display: flex;
    align-items: baseline;
    gap: 12px;
  }

  h1 {
    font-size: 20px;
    font-weight: 600;
    color: #fff;
    letter-spacing: -0.02em;
  }

  .version {
    font-size: 12px;
    color: #888;
    font-weight: 500;
  }

  .connection-status {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 6px;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }

  .status-indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    box-shadow: 0 0 8px currentColor;
    transition: background 0.3s ease;
  }

  .status-text {
    font-size: 13px;
    font-weight: 500;
    color: #e0e0e0;
  }

  .port {
    font-size: 12px;
    color: #888;
    font-family: 'Monaco', 'Menlo', monospace;
  }
</style>
