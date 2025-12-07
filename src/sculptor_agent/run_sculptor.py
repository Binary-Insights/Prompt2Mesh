#!/usr/bin/env python3
"""
Sculptor Agent CLI - Standalone script for image-to-3D modeling
Run from command line with: python run_sculptor.py --input-image path/to/image.png
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

from src.sculptor_agent import SculptorAgent


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Sculptor Agent - Image-to-3D Modeling Agent for Blender",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_sculptor.py --input-image data/sculptor_images/my_drawing.png
  python run_sculptor.py -i reference.jpg --session-id my-session-123
  python run_sculptor.py -i sketch.png --no-resume --verbose
        """
    )
    
    parser.add_argument(
        '--input-image', '-i',
        type=str,
        required=True,
        help='Path to input 2D image file (PNG, JPG, etc.)'
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
    
    parser.add_argument(
        '--resume', '-r',
        action='store_true',
        default=True,
        help='Enable session resume (default: True). Use --no-resume to disable'
    )
    
    parser.add_argument(
        '--no-resume',
        action='store_false',
        dest='resume',
        help='Disable session resume - always start fresh'
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
    log_file = log_dir / f"sculptor_agent_{timestamp}_{session_id[:8]}.log"
    
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
    
    # Generate session ID if not provided
    from uuid import uuid4
    session_id = args.session_id or str(uuid4())
    
    # Setup logging first
    log_file = setup_logging(session_id, args.verbose)
    logger = logging.getLogger(__name__)
    
    # Validate input file
    input_path = Path(args.input_image)
    if not input_path.exists():
        logger.error(f"Input image not found: {args.input_image}")
        print(f"❌ Error: Input image not found: {args.input_image}")
        sys.exit(1)
    
    # Validate image format
    valid_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp'}
    if input_path.suffix.lower() not in valid_extensions:
        logger.error(f"Invalid image format: {input_path.suffix}")
        print(f"❌ Error: Invalid image format. Supported: {', '.join(valid_extensions)}")
        sys.exit(1)
    
    logger.info("="*80)
    logger.info("SCULPTOR AGENT - Image-to-3D Modeling")
    logger.info("="*80)
    logger.info(f"Input Image: {input_path}")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Resume Mode: {args.resume}")
    logger.info(f"Log File: {log_file}")
    logger.info("-"*80)
    
    print("=" * 80)
    print("🗿 SCULPTOR AGENT - Image-to-3D Modeling")
    print("=" * 80)
    print(f"\n📸 Input Image: {input_path}")
    print(f"🔑 Session ID: {session_id}")
    print(f"🔄 Resume Mode: {'Enabled' if args.resume else 'Disabled (fresh start)'}")
    print(f"📝 Log File: {log_file}")
    print("\n" + "-" * 80 + "\n")
    
    # Create agent
    agent = SculptorAgent(
        session_id=session_id,
        display_callback=None  # Uses default console display
    )
    
    try:
        # Initialize agent
        logger.info("Initializing Sculptor Agent...")
        await agent.initialize()
        logger.info("Agent initialized successfully")
        
        print("\n" + "-" * 80 + "\n")
        
        # Run modeling task
        logger.info(f"Starting image-to-3D modeling from: {input_path}")
        results = await agent.run(str(input_path), use_deterministic_session=args.resume)
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
        
        # Display quality scores
        if results.get('quality_scores'):
            print("\n" + "-" * 80)
            print("📈 QUALITY PROGRESSION")
            print("-" * 80)
            for score_info in results['quality_scores']:
                print(f"Step {score_info['step']}: {score_info['score']}%")
            
            avg_score = sum(s['score'] for s in results['quality_scores']) / len(results['quality_scores'])
            print(f"\n📊 Average Quality: {avg_score:.1f}%")
        
        # Display vision analysis summary
        if results.get('vision_analysis'):
            print("\n" + "-" * 80)
            print("👁️ VISION ANALYSIS")
            print("-" * 80)
            analysis = results['vision_analysis']
            print(analysis[:300] + ("..." if len(analysis) > 300 else ""))
        
        if args.verbose:
            logger.info("-"*80)
            logger.info("TOOL EXECUTION SUMMARY")
            logger.info("-"*80)
            for i, tool_result in enumerate(results['tool_results'], 1):
                status = "SUCCESS" if tool_result['success'] else "FAILED"
                logger.info(f"{i}. [{status}] {tool_result['tool_name']}")
                if not tool_result['success']:
                    logger.error(f"   Error: {tool_result['result'][:500]}")
            
            print("\n" + "-" * 80)
            print("🔧 TOOL EXECUTION SUMMARY")
            print("-" * 80)
            for i, tool_result in enumerate(results['tool_results'], 1):
                status = "✅" if tool_result['success'] else "❌"
                print(f"\n{i}. {status} {tool_result['tool_name']}")
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
