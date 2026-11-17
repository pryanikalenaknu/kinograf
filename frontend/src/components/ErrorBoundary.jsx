/** Межа помилок: збій однієї сторінки не прибирає верхню панель і решту застосунку. */

import { Component } from 'react';
import { ErrorState } from './States.jsx';

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return (
        <div className="page">
          <ErrorState
            title="Сторінку не вдалося показати"
            text="Під час відображення сталася помилка. Спробуйте оновити сторінку."
            onRetry={() => this.setState({ failed: false })}
          />
        </div>
      );
    }
    return this.props.children;
  }
}
