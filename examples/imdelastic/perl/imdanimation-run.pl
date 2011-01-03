#!/usr/bin/perl

use Cwd;
use File::Path;
use File::Basename;
use sigtrap 'handler', \&cleanup , 'error-signals' ;
$SIG{PIPE}=\&trap; $SIG{QUIT}=\&trap; $SIG{INT}=\&trap; $SIG{STOP}=\&trap; $SIG{HUP}=\&trap;

sub trap
{
        debug( "Stop!" ) ;
        &cleanup ;
}

	my $out = "imd_out.txt" ;
	my $err = "imd_err.txt" ;
	my $dir = dirname($0) ;
	my $cwd = getcwd ;
	my $jobid = &run( "/usr/bin/perl $dir/make_movie.pl " . join( " " , @ARGV ) , $cwd , undef , $out , $err ) ;
	@jobid = ( $jobid ) ;
	&waitFor( $jobid ) ;

sub run
{
        my ( $cmd , $cwd , $in , $out , $err ) = @_ ;
        my $jobid ;
        my $cmdLine = "cd $cwd ; qsub -b y -cwd -j n -o $out -e $err $cmd " ;
        &debug( "$cmdLine" ) ;
        my $result = `$cmdLine` ;
        if( $result =~ /Your job ([0-9]+) .* has been submitted/mig )
        {
                $jobid = $1 ;
        }
        return $jobid ;
}

sub waitFor
{
        my @jobid = @_ ;
        my %jobs = map { $_ => 1 } @jobid ;
        while( 1 ) {
        my $wait = 0 ;
        my @qstat = `qstat` ;
        foreach( @qstat )
        {
                if( /\s*([0-9]+)\s+/ )
                {
                        my $job = $1 ;
                        if( defined( $jobs{$job} ) )
                        {
                                $wait = 1 ;
                                &debug( "Waiting for $job - still in queue" ) ;
                                last ;
                        }
                }
        }
        if( $wait == 0 )
        {
                last ;
        }
        else
        {
                sleep 2 ;
        }
        }

}

sub cleanup
{
        if( $handled < 10 )
        {

        &debug( "removing " . join( ' ' , @jobid ) . "\n" ) ;
        my $tasklist = join( " " , @jobid ) ;
        `qdel $tasklist` ;
        $handled = $handled + 1 ;
	my $list = ();
	if ( -f "$cwd/mycwd" ) {
		open (FILE, "$cwd/mycwd");
		foreach $line (<FILE>) {
			chomp $line;
			push @list, $line;
		}
		close (FILE);
		my $command = "ssh @list[0] rm -rf @list[1]";
		`$command`;
		`echo "$command" >> /home/gpserver/iran`;
	} 		
	$cwd = getcwd;
	rmtree($cwd);
	`echo "cleanup in imdanimation" >> /home/gpserver/iran`;
	exit;
        }
}

sub debug
{
        print STDERR join( "\n" , @_ ) . "\n" ;
        open FILE , ">>myError.log" ;
        print FILE join( "\n" , @_ ) . "\n" ;
        close FILE ;
}
