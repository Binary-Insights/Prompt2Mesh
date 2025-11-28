#!/usr/bin/env python3
"""
Artisan Agent CLI - Standalone script for 3D modeling automation
Run from command line with: python run_artisan.py --input-file path/to/requirement.json
"""
import asyncio
import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.artisan_agent import ArtisanAgent


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Artisan Agent - Autonomous 3D Modeling Agent for Blender",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_artisan.py --input-file data/prompts/json/20251127_135557_Could_you_model_a_ch.json
  python run_artisan.py -i data/prompts/json/my_requirement.json --session-id my-session-123
        """
    )
    
    parser.add_argument(
        '--input-file', '-i',
        type=str,
        required=True,
        help='Path to input JSON file containing refined_prompt'
    )
    
    parser.add_argument(
        '--session-id', '-s',
        type=str,
        default=None,
        help='Optional session ID (auto-generated if not provided)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser.parse_args()


def setup_logging(session_id: str, verbose: bool = False) -> Path:
    """
    Setup logging to both console and file
    
    Args:
        session_id: Unique session identifier
        verbose: Enable verbose logging
        
    Returns:
        Path to log file
    """
    # Create logs directory
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create log file with timestamp and session ID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"artisan_agent_{timestamp}_{session_id[:8]}.log"
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Set log level based on verbose flag
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            # File handler - always writes all logs
            logging.FileHandler(log_file, mode='w', encoding='utf-8'),
            # Console handler - respects log level
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Create logger for this module
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - Log file: {log_file}")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Verbose mode: {verbose}")
    
    return log_file


async def main():
    """Main execution function"""
    args = parse_arguments()
    
    # Generate session ID if not provided (needed for logging setup)
    from uuid import uuid4
    session_id = args.session_id or str(uuid4())
    
    # Setup logging first
    log_file = setup_logging(session_id, args.verbose)
    logger = logging.getLogger(__name__)
    
    # Validate input file
    input_path = Path(args.input_file)
    if not input_path.exists():
        logger.error(f"Input file not found: {args.input_file}")
        print(f"❌ Error: Input file not found: {args.input_file}")
        sys.exit(1)
    
    if not input_path.suffix == '.json':
        logger.error("Input file must be a JSON file")
        print(f"❌ Error: Input file must be a JSON file")
        sys.exit(1)
    
    logger.info("="*80)
    logger.info("ARTISAN AGENT - Autonomous 3D Modeling")
    logger.info("="*80)
    logger.info(f"Input File: {input_path}")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Log File: {log_file}")
    logger.info("-"*80)
    
    print("=" * 80)
    print("🎨 ARTISAN AGENT - Autonomous 3D Modeling")
    print("=" * 80)
    print(f"\n📄 Input File: {input_path}")
    print(f"🔑 Session ID: {session_id}")
    print(f"📝 Log File: {log_file}")
    print("\n" + "-" * 80 + "\n")
    
    # Create agent
    agent = ArtisanAgent(
        session_id=session_id,
        display_callback=None  # Uses default console display
    )
    
    try:
        # Initialize agent
        logger.info("Initializing Artisan Agent...")
        await agent.initialize()
        logger.info("Agent initialized successfully")
        
        print("\n" + "-" * 80 + "\n")
        
        # Run modeling task
        logger.info(f"Starting modeling task from: {input_path}")
        results = await agent.run(str(input_path))
        logger.info("Modeling task completed")
        
        # Display results
        logger.info("="*80)
        logger.info("MODELING RESULTS")
        logger.info("="*80)
        logger.info(f"Success: {results['success']}")
        logger.info(f"Steps Executed: {results['steps_executed']}")
        logger.info(f"Screenshots Captured: {results['screenshots_captured']}")
        logger.info(f"Screenshot Directory: {results['screenshot_directory']}")
        logger.info(f"Session ID: {results['session_id']}")
        
        print("\n" + "=" * 80)
        print("📊 MODELING RESULTS")
        print("=" * 80)
        print(f"\n✅ Success: {results['success']}")
        print(f"📋 Steps Executed: {results['steps_executed']}")
        print(f"📸 Screenshots Captured: {results['screenshots_captured']}")
        print(f"📁 Screenshot Directory: {results['screenshot_directory']}")
        print(f"🔑 Session ID: {results['session_id']}")
        
        if args.verbose:
            logger.info("-"*80)
            logger.info("TOOL EXECUTION SUMMARY")
            logger.info("-"*80)
            for i, tool_result in enumerate(results['tool_results'], 1):
                status = "SUCCESS" if tool_result['success'] else "FAILED"
                logger.info(f"{i}. [{status}] {tool_result['tool_name']}")
                logger.info(f"   Arguments: {tool_result.get('arguments', {})}")
                if not tool_result['success']:
                    logger.error(f"   Error: {tool_result['result'][:500]}")
            
            print("\n" + "-" * 80)
            print("🔧 TOOL EXECUTION SUMMARY")
            print("-" * 80)
            for i, tool_result in enumerate(results['tool_results'], 1):
                status = "✅" if tool_result['success'] else "❌"
                print(f"\n{i}. {status} {tool_result['tool_name']}")
                print(f"   Arguments: {tool_result.get('arguments', {})}")
                if not tool_result['success']:
                    print(f"   Error: {tool_result['result'][:200]}")
        
        print("\n" + "=" * 80 + "\n")
        
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        print("\n\n⚠️ Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        if args.verbose:
            import traceback
            logger.error("Full traceback:")
            logger.error(traceback.format_exc())
            traceback.print_exc()
        print(f"\n\n❌ Error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup
        logger.info("Starting cleanup...")
        try:
            await agent.cleanup()
            logger.info("Cleanup completed successfully")
        except Exception as cleanup_error:
            # Suppress cleanup errors
            logger.warning(f"Cleanup error (suppressed): {cleanup_error}")
            pass
        print("🧹 Cleanup complete")
        logger.info("="*80)
        logger.info(f"Session completed - Log saved to: {log_file}")
        logger.info("="*80)
        # Give asyncio time to clean up properly
        try:
            await asyncio.sleep(0.1)
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
